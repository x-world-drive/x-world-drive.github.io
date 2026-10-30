"""Convert a saved Feishu document to a portable, escaped article snapshot.

usage: import_article.py en|zh

Run after scripts/prepare_media.py. Only known content tags are supported so a changed
document cannot silently drop an embed or introduce executable markup into the published
page. The article text is the document's own; only site labels are added here.
"""
from pathlib import Path
from html import escape
from urllib.parse import urlparse
import json
import math
import re
import struct
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = {
    'en': {
        'document': 'source/feishu-document-en.json',
        'source': 'https://xiaopeng.feishu.cn/wiki/EImjwGTUTixbdvk5SOtclUeHnkb',
        'overview': 'Optimization Overview',
        'zoom': 'Enlarge: ',
        'lead': [('videos', 'Demo Videos'), ('introduction', 'Background'), ('optimization-overview', 'Optimization Overview')],
        'sections': ['Breakable CUDA Graph', 'UCP Multi-GPU', 'Kernel-Level Optimization', 'Lowering Control Latency',
                     'Seven-View VAE Decoding', 'Miscellaneous and Network Optimization', 'End-to-End Inference RSI', 'Acknowledgments'],
        'description': "We optimized X-World 1.5's online GPU inference, codecs and request scheduling to raise the "
                       'seven-view frame rate and shorten the delay from a control input to the updated frame.',
        'minutes': lambda text: math.ceil(len(text.split()) / 230),
    },
    'zh': {
        'document': 'source/feishu-document.json',
        'source': 'https://xiaopeng.feishu.cn/wiki/XDG6wIlYmi8sNLkewjvcAN11n8g',
        'overview': '优化总览',
        'zoom': '放大：',
        'lead': [('videos', '演示视频'), ('introduction', '背景与目标'), ('optimization-overview', '优化总览')],
        'sections': ['Breakable CUDA Graph', 'UCP 多卡并行', 'Kernel 层优化', '降低操控延迟',
                     '七路 VAE 解码优化', '其他杂项与网络传输优化', '推理全流程 RSI', '致谢'],
        'description': '我们优化了 X-World 1.5 的线上 GPU 推理、编解码和请求调度，提高七路画面的生成帧率，缩短操作到画面更新的延迟。',
        'minutes': lambda text: math.ceil(len(text) / 450),
    },
}
lang = sys.argv[1]
config = LANGUAGES[lang]
doc = json.loads((ROOT / config['document']).read_text())['data']['document']
root = ET.fromstring('<document>' + doc['content'] + '</document>')
manifest = json.loads((ROOT / 'source/media-manifest.json').read_text())
assets = {m['token']: m for m in manifest}
figures = []
FIGURE = '\x00'


def content(node):
    return escape(node.text or '') + ''.join(render(child) + escape(child.tail or '') for child in node)


def render(node):
    tag = node.tag
    if tag in ('span',):
        return content(node)
    if tag == 'img':
        asset = assets[node.get('src')]
        path = ROOT / asset['original']
        width, height = struct.unpack('>II', path.read_bytes()[16:24])
        figures.append({'id': node.get('id'), 'name': Path(node.get('name')).stem, 'src': 'images/' + asset['name'],
                        'width': width, 'height': height, 'caption': node.get('caption', '').strip(),
                        'zoom': config['zoom']})
        return FIGURE
    if tag == 'a':
        href = node.get('href', '')
        if href.startswith(config['source'] + '#'):
            href = '#' + href.split('#', 1)[1]
        elif urlparse(href).scheme not in ('https', 'http') or 'feishu.cn' in href:
            raise ValueError(f'Unsupported link: {href}')
        external = ' target="_blank" rel="noopener noreferrer"' if not href.startswith('#') else ''
        return f'<a href="{escape(href, quote=True)}"{external}>{content(node)}</a>'
    if tag == 'br':
        return '<br />'
    if tag == 'colgroup':
        return ''
    if tag == 'callout':
        attrs = f' id="{escape(node.get("id"))}"' if node.get('id') else ''
        return f'<aside class="tldr-callout"{attrs} aria-label="TL;DR">{content(node)}</aside>'
    if tag == 'table':
        return (f'<div class="table-scroll" role="region" aria-label="{config["overview"]}" tabindex="0">'
                f'<table>{content(node)}</table></div>')
    if tag == 'p' and not ''.join(node.itertext()).strip():
        return ''
    if tag in ('p', 'h2') and ''.join(node.itertext()).strip() == config['overview']:
        return f'<h2 id="optimization-overview">{config["overview"]}</h2>'
    if tag in ('p', 'h2', 'h3', 'b', 'code', 'ul', 'ol', 'li', 'thead', 'tbody', 'tr', 'th', 'td'):
        attrs = f' id="{escape(node.get("id"))}"' if node.get('id') else ''
        attrs += ' scope="col"' if tag == 'th' else ''
        return f'<{tag}{attrs}>{content(node)}</{tag}>'
    raise ValueError(f'Unmapped content tag: {tag}')


headings = [{'id': anchor, 'text': text, 'depth': 2} for anchor, text in config['lead']]
sections = iter(config['sections'])
for node in root.iter():
    if node.tag in ('h2', 'h3') and ''.join(node.itertext()).strip() != config['overview']:
        text = next(sections) if node.tag == 'h2' else ''.join(node.itertext())
        headings.append({'id': node.get('id'), 'text': text, 'depth': int(node.tag[1])})
assert next(sections, None) is None, 'Every section label must match a heading'

videos = []
for index, asset in enumerate((m for m in manifest if m['kind'] == 'video'), 1):
    videos.append({'id': f'video-{index:02d}', 'src': asset['public'].removeprefix('public/'),
                   'poster': asset['poster'].removeprefix('public/'),
                   'title': asset['titles'][lang], 'label': asset['labels'][lang],
                   'kind': asset['video_kind'], 'durationSeconds': asset['duration_seconds'],
                   'width': asset['width'], 'height': asset['height']})

body = '\n'.join(render(n) for n in root if n.tag not in ('title', 'grid', 'figure'))


def cross_links(html):
    """Link "第 N 节 / Section N" to its heading and "图 N / Figure N" to its figure, outside links and headings."""
    sections = [h['id'] for h in headings[len(config['lead']):] if h['depth'] == 2]
    ref = re.compile(r'第 ?(\d+) ?节|图 ?(\d+)[a-z]?' if lang == 'zh' else r'Sections? (\d+)|Figures? (\d+)[a-z]?')

    def link(match):
        number = int(match[1] or match[2])
        targets = [f['id'] for f in figures] if match[2] else sections
        return f'<a href="#{targets[number - 1]}">{match[0]}</a>' if number <= len(targets) else match[0]

    out, inside = [], 0
    for token in re.split(r'(<[^>]+>)', html):
        tag = re.match(r'<(/?)(a|h2|h3)\b', token)
        if tag:
            inside += -1 if tag[1] else 1
        out.append(token if token.startswith('<') or inside else ref.sub(link, token))
    return ''.join(out)


body = cross_links(body)
segments = []
for index, html in enumerate(body.split(FIGURE)):
    if html.strip():
        segments.append({'html': html})
    if index < len(figures):
        segments.append({'figure': figures[index]})
plain = ''.join(root.itertext())
result = {
    'lang': lang,
    'title': ''.join(root.find('title').itertext()),
    'description': config['description'],
    'updated': '2026-10-28',
    'revision': doc['revision_id'],
    'readingMinutes': config['minutes'](plain),
    'headings': headings,
    'videos': videos,
    'segments': segments,
}
(ROOT / 'src/data').mkdir(parents=True, exist_ok=True)
(ROOT / f'src/data/article-{lang}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(f'Imported {lang} revision {doc["revision_id"]}: {len(videos)} videos, '
      f'{len(list(root.iter("img")))} figures, {len(plain)} characters.')
