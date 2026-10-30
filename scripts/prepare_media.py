"""Make browser-friendly media from the downloaded Feishu attachments, under content-hash names.

Run in a local venv with imageio-ffmpeg after saving both documents and downloading their media:
source/feishu-document.json (zh), source/feishu-document-en.json (en), source/media/video-NN.mp4 in
the zh document's order, and source/media/<lang>-<image name>. Videos are remuxed without re-encoding
and moved to faststart; figures are copied byte for byte. Writes source/media-manifest.json.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = {'zh': ROOT / 'source/feishu-document.json', 'en': ROOT / 'source/feishu-document-en.json'}
TITLES = json.loads((ROOT / 'scripts/video_titles.json').read_text())
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()


def tags(content, name):
    return [dict(re.findall(r'(\w[\w-]*)="([^"]*)"', tag)) for tag in re.findall(rf'<{name}\b[^>]*/?>', content)]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()[:20]


for folder in ('public/media', 'public/images'):
    shutil.rmtree(ROOT / folder, ignore_errors=True)
    (ROOT / folder).mkdir(parents=True)

manifest = []
contents = {lang: json.loads(path.read_text())['data']['document']['content'] for lang, path in DOCUMENTS.items()}
for index, (source_tag, titles) in enumerate(zip(tags(contents['zh'], 'source'), TITLES, strict=True), 1):
    original = ROOT / f'source/media/video-{index:02d}.mp4'
    name = f'{digest(original)}.mp4'
    output = ROOT / 'public/media' / name
    subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(original), '-map', '0:v:0',
                    '-map', '0:a?', '-map_metadata', '-1', '-c', 'copy', '-movflags', '+faststart', str(output)],
                   check=True)
    poster = output.with_name(output.stem + '-poster.jpg')
    subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-ss', '12', '-i', str(output),
                    '-frames:v', '1', '-vf', 'scale=960:-2', '-q:v', '3', str(poster)], check=True)
    frames = imageio_ffmpeg.read_frames(str(output))
    metadata = next(frames)
    frames.close()
    manifest.append({'token': source_tag['token'], 'kind': 'video', 'original': str(original.relative_to(ROOT)),
                     'public': str(output.relative_to(ROOT)), 'poster': str(poster.relative_to(ROOT)),
                     'name': name, 'video_kind': titles['kind'], 'titles': titles['titles'],
                     'labels': titles['labels'], 'duration_seconds': metadata['duration'],
                     'width': metadata['size'][0], 'height': metadata['size'][1]})
    print(f'{original.name} -> {name}: {output.stat().st_size} bytes', flush=True)

for lang, content in contents.items():
    for image in tags(content, 'img'):
        original = ROOT / f'source/media/{lang}-{image["name"]}'
        name = f'{digest(original)}{original.suffix}'
        shutil.copyfile(original, ROOT / 'public/images' / name)
        manifest.append({'token': image['src'], 'kind': 'image', 'original': str(original.relative_to(ROOT)),
                         'public': f'public/images/{name}', 'name': name})

(ROOT / 'source/media-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(f'{sum(m["kind"] == "video" for m in manifest)} videos, '
      f'{len({m["name"] for m in manifest if m["kind"] == "image"})} distinct figures.')
