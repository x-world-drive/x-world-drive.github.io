"""Check the built site's content coverage, assets, links and MP4 streaming layout."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import json
import os
import re
import struct
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
BASE = os.environ.get('BASE_PATH', '/').rstrip('/')


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.tags, self.ids, self.links, self.text = [], [], [], []
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        for attr in ('src', 'href', 'poster'):
            if attrs.get(attr):
                self.links.append(attrs[attr])

    def handle_data(self, data):
        self.text.append(data)


pages = {p: Page(p) for p in DIST.rglob('*.html')}
assert pages, 'Build the site first'
for path, page in pages.items():
    duplicates = [key for key, count in Counter(page.ids).items() if count > 1]
    assert not duplicates, (path, 'duplicate IDs', duplicates)
    for url in page.links:
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc:
            continue
        local = unquote(parsed.path)
        if not local:
            target = path
        elif local.startswith('/'):
            assert not BASE or local.startswith(BASE + '/'), (path, 'asset misses base path', url)
            target = DIST / local.removeprefix(BASE).lstrip('/')
        else:
            target = path.parent / local
        if target.is_dir():
            target /= 'index.html'
        assert target.is_file(), (path, 'missing resource', url)
        if parsed.fragment and target.suffix == '.html':
            assert unquote(parsed.fragment) in pages[target].ids, (path, 'missing anchor', url)

PAGES = {'en': DIST / 'index.html', 'zh': DIST / 'zh/index.html'}
# Figures drawn by components in src/components/figures carry the site's own captions.
INTERACTIVE = set(re.findall(r'(\w+): [A-Z]\w+[,\n]', (ROOT / 'src/components/Figure.astro').read_text()))
DOCUMENTS = {'en': ROOT / 'source/feishu-document-en.json', 'zh': ROOT / 'source/feishu-document.json'}
normalize = lambda text: re.sub(r'\s+', '', text)
for lang, path in PAGES.items():
    home = pages[path]
    assert any(tag == 'html' and attrs.get('lang') == ('en' if lang == 'en' else 'zh-CN') for tag, attrs in home.tags), (lang, 'page language')
    article = json.loads((ROOT / f'src/data/article-{lang}.json').read_text())
    videos = [attrs for tag, attrs in home.tags if tag == 'video']
    video_sources = [attrs['src'] for tag, attrs in home.tags if tag == 'source' and attrs.get('type') == 'video/mp4']
    figures = [attrs for tag, attrs in home.tags if tag == 'figure' and 'article-figure' in attrs.get('class', '').split()]
    images = [attrs for tag, attrs in home.tags if tag == 'img' and '/images/' in attrs.get('src', '')]
    assert len(videos) == len(article['videos']) == 5, (lang, 'All imported videos must be present')
    assert Counter(video_sources) == Counter(BASE + '/' + video['src'] for video in article['videos']), 'Video sources must match the content manifest'
    expected_figures = json.loads(DOCUMENTS[lang].read_text())['data']['document']['content'].count('<img ')
    assert len(figures) == expected_figures, (lang, f'All {expected_figures} source figures must be present')
    assert all(v.get('preload') == 'none' and 'controls' in v and 'autoplay' not in v for v in videos)
    assert all(f.get('alt') and f.get('width') and f.get('height') for f in images)
    assert 'route-note' in home.ids, (lang, 'the AR route guidance note must be on the page')
    source_file = DOCUMENTS[lang]
    if source_file.exists():
        source = json.loads(source_file.read_text())['data']['document']['content']
        source = ET.fromstring('<doc>' + source + '</doc>')
        actual = normalize(''.join(home.text))
        checked = 0
        for node in source.iter():
            if node.tag in ('p', 'h2', 'h3', 'title'):
                expected = normalize(''.join(node.itertext()))
                if expected:
                    assert expected in actual, (lang, 'Missing source text', expected[:100])
                    checked += 1
            elif node.tag == 'img' and Path(node.get('name', '')).stem not in INTERACTIVE:
                assert normalize(node.get('caption', '')) in actual
        print(f'{lang}: {checked} text blocks and {expected_figures} captions preserved.')

# Inspect MP4 box order without reading the entire video into memory.
for video in (DIST / 'media').glob('*.mp4'):
    boxes = []
    with video.open('rb') as stream:
        while header := stream.read(8):
            size, box = struct.unpack('>I4s', header)
            header_size = 8
            if size == 1:
                size = struct.unpack('>Q', stream.read(8))[0]
                header_size = 16
            boxes.append(box)
            if size == 0:
                break
            assert size >= header_size, (video, 'invalid MP4 box')
            stream.seek(size - header_size, 1)
    assert boxes.index(b'moov') < boxes.index(b'mdat'), (video, 'missing faststart')

print(f'Passed: {len(pages)} pages, internal links and anchors, 5 videos and every figure per language, MP4 faststart.')
