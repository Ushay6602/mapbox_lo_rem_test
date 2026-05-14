"""
Download Mapbox assets for Slovenia.

Supported styles:
- streets: raster tiles into tiles/
- satellite: raster tiles into tiles_sat/
- 3d: style JSON, sprite, glyphs and vector tiles into styles/, sprites/, glyphs/, vectors/

Examples:
  set MAPBOX_TOKEN=your_token
  python download_tiles.py --style streets --min-zoom 6 --max-zoom 10
  python download_tiles.py --style satellite --min-zoom 6 --max-zoom 10
  python download_tiles.py --style 3d --min-zoom 6 --max-zoom 12
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Iterable

import mercantile
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

MAPBOX_TOKEN = os.environ.get('MAPBOX_TOKEN')
SLOVENIA_BBOX = (13.38, 45.42, 16.61, 46.88)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def make_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['GET'],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session


def existing_tile_path(dest_dir: Path, y: int, force: bool) -> Path | None:
    if force:
        return None
    for ext in ('png', 'webp', 'jpg', 'pbf'):
        candidate = dest_dir / f'{y}.{ext}'
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate
    return None


def download_file(session: requests.Session, url: str, dest: Path) -> str:
    try:
        response = session.get(url, stream=True, timeout=30)
    except Exception as exc:
        return f'error network {exc}'

    if response.status_code != 200:
        body = ''
        try:
            body = response.text[:240]
        except Exception:
            pass
        return f'error http {response.status_code} {body}'

    ensure_dir(dest.parent)
    fd, tmp_path = tempfile.mkstemp(dir=str(dest.parent))
    try:
        with os.fdopen(fd, 'wb') as handle:
            for chunk in response.iter_content(1024 * 8):
                if chunk:
                    handle.write(chunk)
        shutil.move(tmp_path, dest)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    return 'downloaded'


def raster_tile_url(style_name: str, z: int, x: int, y: int, token: str) -> str:
    if style_name == 'satellite':
        style_id = 'satellite-streets-v12'
    else:
        style_id = 'streets-v12'
    return f'https://api.mapbox.com/styles/v1/mapbox/{style_id}/tiles/256/{z}/{x}/{y}?access_token={token}'


def raster_out_root(out: Path, style_name: str) -> Path:
    return out / ('tiles_sat' if style_name == 'satellite' else 'tiles')


def download_raster_tiles(session: requests.Session, token: str, out: Path, style_name: str, zooms: range, force: bool, workers: int, sleep_seconds: float) -> None:
    out_root = raster_out_root(out, style_name)
    all_tiles = []
    for z in zooms:
        z_tiles = list(mercantile.tiles(*SLOVENIA_BBOX, [z]))
        print(f'Zoom {z}: {len(z_tiles)} tiles')
        all_tiles.extend((style_name, out_root, token, t.z, t.x, t.y, force) for t in z_tiles)

    total = len(all_tiles)
    print(f'Starting raster download ({style_name}) with {workers} workers; total tiles: {total}')

    def worker(item):
        _, out_root_, token_, z, x, y, force_ = item
        dest_dir = out_root_ / str(z) / str(x)
        existing = existing_tile_path(dest_dir, y, force_)
        if existing is not None:
            return 'skipped'
        url = raster_tile_url(style_name, z, x, y, token_)
        dest = dest_dir / f'{y}.png'
        status = download_file(session, url, dest)
        if sleep_seconds:
            time.sleep(sleep_seconds)
        return status

    downloaded = skipped = errors = 0
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(worker, item) for item in all_tiles]
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            status = future.result()
            if status == 'downloaded':
                downloaded += 1
            elif status == 'skipped':
                skipped += 1
            else:
                errors += 1
                print(f'ERROR: {status}')
            if index % 200 == 0:
                elapsed = time.time() - start
                print(f'  processed={index}/{total} downloaded={downloaded} skipped={skipped} errors={errors} elapsed={elapsed:.1f}s')

    elapsed = time.time() - start
    print(f'DONE: total={total} downloaded={downloaded} skipped={skipped} errors={errors} time={elapsed:.1f}s')


def download_text(session: requests.Session, url: str) -> dict:
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def rewrite_style(style: dict, style_name: str) -> dict:
    rewritten = json.loads(json.dumps(style))
    rewritten['sprite'] = f'/sprites/{style_name}/sprite'
    rewritten['glyphs'] = f'/glyphs/{style_name}/{{fontstack}}/{{range}}.pbf'
    for source_name, source in rewritten.get('sources', {}).items():
        source_type = source.get('type')
        url = source.get('url', '')
        if source_type == 'vector' and url.startswith('mapbox://'):
            tileset = url.replace('mapbox://', '')
            source.pop('url', None)
            source['tiles'] = [f'/vectors/{style_name}/{tileset}/{{z}}/{{x}}/{{y}}.pbf']
            source['minzoom'] = source.get('minzoom', 0)
            source['maxzoom'] = source.get('maxzoom', 14)
    building_layer = {
        'id': '3d-buildings',
        'source': 'composite',
        'source-layer': 'building',
        'filter': ['==', 'extrude', 'true'],
        'type': 'fill-extrusion',
        'minzoom': 15,
        'paint': {
            'fill-extrusion-color': '#a9b4c7',
            'fill-extrusion-height': ['coalesce', ['to-number', ['get', 'height']], 0],
            'fill-extrusion-base': ['coalesce', ['to-number', ['get', 'min_height']], 0],
            'fill-extrusion-opacity': 0.72,
        },
    }
    layers = rewritten.get('layers', [])
    if not any(layer.get('id') == '3d-buildings' for layer in layers):
        insert_at = next((i + 1 for i, layer in enumerate(layers) if layer.get('type') == 'symbol' and layer.get('layout', {}).get('text-field')), len(layers))
        layers.insert(insert_at, building_layer)
        rewritten['layers'] = layers
    return rewritten


def sprite_urls(style: dict) -> list[tuple[str, str]]:
    base = style.get('sprite')
    if not base:
        return []
    return [
        (base + '.json', 'sprite.json'),
        (base + '.png', 'sprite.png'),
        (base + '.webp', 'sprite.webp'),
        (base + '@2x.png', 'sprite@2x.png'),
        (base + '@2x.webp', 'sprite@2x.webp'),
    ]


def glyph_urls(style: dict) -> set[str]:
    glyphs_base = style.get('glyphs', '')
    fontstacks = set()
    for layer in style.get('layers', []):
        fonts = layer.get('layout', {}).get('text-font')
        if isinstance(fonts, list) and fonts:
            fontstacks.add(','.join(fonts))
    ranges = ['0-255', '256-511', '512-767', '768-1023', '1024-1279', '1280-1535', '1536-1791']
    urls = set()
    for fontstack in fontstacks:
        for glyph_range in ranges:
            urls.add(glyphs_base.replace('{fontstack}', fontstack).replace('{range}', glyph_range))
    return urls


def download_style_package(session: requests.Session, token: str, out: Path, zooms: range, force: bool) -> None:
    style_name = 'streets-v12'
    style_url = f'https://api.mapbox.com/styles/v1/mapbox/{style_name}?access_token={token}'
    style = download_text(session, style_url)

    styles_dir = out / 'styles'
    sprite_dir = styles_dir / style_name
    glyphs_dir = out / 'glyphs' / style_name
    vectors_dir = out / 'vectors' / style_name
    ensure_dir(styles_dir)
    ensure_dir(sprite_dir)
    ensure_dir(glyphs_dir)
    ensure_dir(vectors_dir)

    local_style = rewrite_style(style, style_name)
    local_style_path = styles_dir / f'{style_name}-local.json'
    local_style_path.write_text(json.dumps(local_style, indent=2), encoding='utf-8')
    print(f'Saved local style: {local_style_path}')

    for url, filename in sprite_urls(style):
        dest = sprite_dir / filename
        if dest.exists() and dest.stat().st_size > 0 and not force:
            continue
        print(f'Downloading sprite asset: {filename}')
        result = download_file(session, url, dest)
        if result != 'downloaded':
            print(f'ERROR sprite {filename}: {result}')

    for url in sorted(glyph_urls(style)):
        rel = url.split('/fonts/v1/')[-1]
        dest = glyphs_dir / rel
        if dest.exists() and dest.stat().st_size > 0 and not force:
            continue
        result = download_file(session, url, dest)
        if result != 'downloaded':
            print(f'ERROR glyph {rel}: {result}')

    # Download vector tiles for all vector sources referenced by the style.
    sources = style.get('sources', {})
    vector_tilesets = []
    for source in sources.values():
        if source.get('type') == 'vector' and source.get('url', '').startswith('mapbox://'):
            vector_tilesets.append(source['url'].replace('mapbox://', ''))

    vector_tilesets = sorted(set(vector_tilesets))
    if not vector_tilesets:
        print('No vector sources found in style JSON.')
        return

    all_jobs = []
    for tileset in vector_tilesets:
        for z in zooms:
            z_tiles = list(mercantile.tiles(*SLOVENIA_BBOX, [z]))
            print(f'Vector tileset {tileset} zoom {z}: {len(z_tiles)} tiles')
            for t in z_tiles:
                all_jobs.append((tileset, z, t.x, t.y))

    print(f'Downloading vector tiles: {len(all_jobs)} jobs')

    def worker(job):
        tileset, z, x, y = job
        dest_dir = vectors_dir / tileset / str(z) / str(x)
        dest = dest_dir / f'{y}.pbf'
        if dest.exists() and dest.stat().st_size > 0 and not force:
            return 'skipped'
        url = f'https://api.mapbox.com/v4/{tileset}/{z}/{x}/{y}.vector.pbf?access_token={token}'
        return download_file(session, url, dest)

    downloaded = skipped = errors = 0
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(worker, job) for job in all_jobs]
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            status = future.result()
            if status == 'downloaded':
                downloaded += 1
            elif status == 'skipped':
                skipped += 1
            else:
                errors += 1
                print(f'ERROR: {status}')
            if index % 200 == 0:
                elapsed = time.time() - start
                print(f'  vector progress={index}/{len(all_jobs)} downloaded={downloaded} skipped={skipped} errors={errors} elapsed={elapsed:.1f}s')

    elapsed = time.time() - start
    print(f'VECTOR DONE: total={len(all_jobs)} downloaded={downloaded} skipped={skipped} errors={errors} time={elapsed:.1f}s')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--style', choices=['streets', 'satellite', '3d'], default='streets')
    parser.add_argument('--min-zoom', type=int, default=6)
    parser.add_argument('--max-zoom', type=int, default=10)
    parser.add_argument('--out', default='.')
    parser.add_argument('--token', default=None)
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--sleep', type=float, default=0.0)
    parser.add_argument('--no-sleep', action='store_true')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--max-tiles', type=int, default=0)
    args = parser.parse_args()

    token = args.token or MAPBOX_TOKEN
    if not token:
        raise SystemExit('Mapbox token required via MAPBOX_TOKEN env or --token')

    out = Path(args.out)
    session = make_session()
    zooms = range(args.min_zoom, args.max_zoom + 1)
    sleep_seconds = 0.0 if args.no_sleep else args.sleep

    if args.style in ('streets', 'satellite'):
        total = sum(len(list(mercantile.tiles(*SLOVENIA_BBOX, [z]))) for z in zooms)
        for z in zooms:
            print(f'Zoom {z}: {len(list(mercantile.tiles(*SLOVENIA_BBOX, [z])))} tiles')
        if args.dry_run:
            print(f'DRY RUN: total tiles to process: {total}')
            return
        if args.max_tiles and total > args.max_tiles:
            print(f'Aborting: total tiles {total} exceeds --max-tiles {args.max_tiles}')
            return
        download_raster_tiles(session, token, out, args.style, zooms, args.force, args.workers, sleep_seconds)
        return

    # 3D package
    if args.dry_run:
        print('DRY RUN: 3D package will download style, sprite, glyphs and vector tiles for the selected zoom range.')
        return
    download_style_package(session, token, out, zooms, args.force)


if __name__ == '__main__':
    main()
