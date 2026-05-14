from flask import Flask, render_template, request, send_from_directory, abort, make_response, jsonify
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

app = Flask(__name__, template_folder='templates', static_folder='static')

MAPBOX_TOKEN = os.environ.get('MAPBOX_TOKEN', 'YOUR_MAPBOX_TOKEN')

# Slovenia bounding box and centre (lon_min, lat_min, lon_max, lat_max)
SLOVENIA_BBOX = [13.38, 45.42, 16.61, 46.88]
SLO_CENTRE = [46.07, 14.55]


def set_cache_headers(response, max_age=86400 * 365, nocache=False):
    """Set cache headers (or disable cache if nocache=True for testing)"""
    if nocache:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        # Remove conditional headers to avoid 304 responses served from cache
        response.headers.pop('ETag', None)
        response.headers.pop('Last-Modified', None)
    else:
        response.headers['Cache-Control'] = f'public, max-age={max_age}, immutable'
        response.headers['Expires'] = (datetime.utcnow() + timedelta(seconds=max_age)).strftime('%a, %d %b %Y %H:%M:%S GMT')
    return response


def highest_tile_zoom(base_dir: str) -> int | None:
    """Return the highest numeric zoom directory that contains at least one tile."""
    if not os.path.isdir(base_dir):
        return None

    zoom_levels = []
    for entry in os.listdir(base_dir):
        zoom_dir = os.path.join(base_dir, entry)
        if not entry.isdigit() or not os.path.isdir(zoom_dir):
            continue
        try:
            has_tiles = any(os.scandir(zoom_dir))
        except OSError:
            has_tiles = False
        if has_tiles:
            zoom_levels.append(int(entry))

    return max(zoom_levels) if zoom_levels else None


@app.route('/')
def index():
    source = request.args.get('source', 'remote')
    style = request.args.get('style', 'streets')
    try:
        lat = float(request.args.get('lat', SLO_CENTRE[0]))
        lon = float(request.args.get('lon', SLO_CENTRE[1]))
        zoom = float(request.args.get('zoom', 7))
    except (ValueError, TypeError):
        lat, lon, zoom = SLO_CENTRE[0], SLO_CENTRE[1], 7
    
    token_ok = bool(MAPBOX_TOKEN and MAPBOX_TOKEN != 'YOUR_MAPBOX_TOKEN')
    tiles_dir = os.path.join(app.root_path, 'tiles')
    tiles_sat_dir = os.path.join(app.root_path, 'tiles_sat')
    styles_dir = os.path.join(app.root_path, 'styles')
    has_local_tiles = os.path.isdir(tiles_dir) and any(os.scandir(tiles_dir))
    has_local_sat = os.path.isdir(tiles_sat_dir) and any(os.scandir(tiles_sat_dir))
    local_tiles_max_zoom = highest_tile_zoom(tiles_dir)
    local_sat_max_zoom = highest_tile_zoom(tiles_sat_dir)
    has_local_3d = os.path.isfile(os.path.join(styles_dir, 'streets-v12-local.json'))
    return render_template(
        'map.html',
        mapbox_token=MAPBOX_TOKEN,
        source=source,
        style=style,
        lat=lat,
        lon=lon,
        zoom=zoom,
        bbox=SLOVENIA_BBOX,
        centre=SLO_CENTRE,
        token_ok=token_ok,
        max_zoom=18,
        has_local_tiles=has_local_tiles,
        has_local_sat=has_local_sat,
        has_local_3d=has_local_3d,
        local_tiles_max_zoom=local_tiles_max_zoom,
        local_sat_max_zoom=local_sat_max_zoom,
    )


@app.route('/tiles/<int:z>/<int:x>/<int:y>.png')
def tiles(z, x, y):
    tiles_dir = os.path.join(app.root_path, 'tiles')
    tile_dir = os.path.join(tiles_dir, str(z), str(x))
    nocache = request.args.get('nocache', '0') == '1'
    
    # Try multiple extensions (png, webp, jpg) since downloader may save in different formats
    for ext in ['png', 'webp', 'jpg']:
        tile_path = os.path.join(tile_dir, f"{y}.{ext}")
        if os.path.exists(tile_path) and os.path.getsize(tile_path) > 0:
            # disable conditional responses so browser won't receive 304 from cache
            response = make_response(send_from_directory(tile_dir, f"{y}.{ext}", conditional=False))
            return set_cache_headers(response, nocache=nocache)
    
    abort(404)


@app.route('/tiles_sat/<int:z>/<int:x>/<int:y>.png')
def tiles_sat(z, x, y):
    tiles_dir = os.path.join(app.root_path, 'tiles_sat')
    tile_dir = os.path.join(tiles_dir, str(z), str(x))
    nocache = request.args.get('nocache', '0') == '1'
    for ext in ['png', 'webp', 'jpg']:
        tile_path = os.path.join(tile_dir, f"{y}.{ext}")
        if os.path.exists(tile_path) and os.path.getsize(tile_path) > 0:
            response = make_response(send_from_directory(tile_dir, f"{y}.{ext}", conditional=False))
            return set_cache_headers(response, nocache=nocache)
    abort(404)


@app.route('/styles/<path:style_name>.json')
def local_style(style_name):
    styles_dir = os.path.join(app.root_path, 'styles')
    path = os.path.join(styles_dir, f'{style_name}.json')
    nocache = request.args.get('nocache', '0') == '1'
    if os.path.exists(path):
        response = make_response(send_from_directory(styles_dir, f'{style_name}.json', conditional=False))
        return set_cache_headers(response, nocache=nocache)
    abort(404)


@app.route('/sprites/<style_name>/<path:file_name>')
def local_sprite(style_name, file_name):
    sprite_dir = os.path.join(app.root_path, 'styles', style_name)
    path = os.path.join(sprite_dir, file_name)
    nocache = request.args.get('nocache', '0') == '1'
    if os.path.exists(path):
        response = make_response(send_from_directory(sprite_dir, file_name, conditional=False))
        return set_cache_headers(response, nocache=nocache)
    abort(404)


@app.route('/glyphs/<style_name>/<path:fontstack>/<range_name>.pbf')
def local_glyph(style_name, fontstack, range_name):
    glyph_dir = os.path.join(app.root_path, 'glyphs', style_name, fontstack)
    path = os.path.join(glyph_dir, f'{range_name}.pbf')
    nocache = request.args.get('nocache', '0') == '1'
    if os.path.exists(path):
        response = make_response(send_from_directory(glyph_dir, f'{range_name}.pbf', conditional=False))
        return set_cache_headers(response, nocache=nocache)
    abort(404)


@app.route('/vectors/<style_name>/<tileset>/<int:z>/<int:x>/<int:y>.pbf')
def local_vector(style_name, tileset, z, x, y):
    vector_dir = os.path.join(app.root_path, 'vectors', style_name, tileset, str(z), str(x))
    path = os.path.join(vector_dir, f'{y}.pbf')
    nocache = request.args.get('nocache', '0') == '1'
    if os.path.exists(path):
        response = make_response(send_from_directory(vector_dir, f'{y}.pbf', conditional=False))
        return set_cache_headers(response, nocache=nocache)
    abort(404)


@app.route('/status')
def status():
    tiles_dir = os.path.join(app.root_path, 'tiles')
    tile_count = 0
    for root, dirs, files in os.walk(tiles_dir) if os.path.exists(tiles_dir) else []:
        for f in files:
            if f.endswith(('.png', '.webp', '.jpg')):
                tile_count += 1
    return {
        'token_ok': bool(MAPBOX_TOKEN and MAPBOX_TOKEN != 'YOUR_MAPBOX_TOKEN'),
        'mapbox_token': None if not (MAPBOX_TOKEN and MAPBOX_TOKEN != 'YOUR_MAPBOX_TOKEN') else 'set',
        'local_tiles': tile_count,
    }


@app.route('/log-perf', methods=['POST'])
def log_perf():
    """Receive performance metrics from the page and store them."""
    data = request.get_json() or {}
    log_dir = Path(app.root_path) / 'perf_logs'
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = log_dir / f'perf_{timestamp}_{data.get("source", "unknown")}_{data.get("style", "unknown")}_z{data.get("zoom", "0")}.json'
    
    # Add server-side timestamp
    data['logged_at'] = datetime.now().isoformat()
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    return {'status': 'logged', 'filename': filename.name}


@app.route('/perf-report')
def perf_report():
    """Return a summary of all performance logs collected."""
    log_dir = Path(app.root_path) / 'perf_logs'
    if not log_dir.exists():
        return {'logs': [], 'summary': 'No logs yet.'}
    
    logs = []
    for log_file in sorted(log_dir.glob('*.json')):
        try:
            with open(log_file) as f:
                data = json.load(f)
                logs.append(data)
        except Exception as e:
            pass
    
    if not logs:
        return {'logs': [], 'summary': 'No logs yet.'}

    requested_session_id = request.args.get('session_id')
    include_all = request.args.get('all', '0') == '1'

    if requested_session_id:
        active_logs = [log for log in logs if log.get('session_id') == requested_session_id]
        active_session_id = requested_session_id
    elif include_all:
        active_logs = logs
        active_session_id = None
    else:
        # Default to the newest session so old measurements from different locations do not mix into the report.
        latest_session_log = max(
            logs,
            key=lambda item: item.get('logged_at', '')
        )
        active_session_id = latest_session_log.get('session_id')
        if active_session_id:
            active_logs = [log for log in logs if log.get('session_id') == active_session_id]
        else:
            active_logs = logs

    if not active_logs:
        return {
            'logs': [],
            'summary': 'No logs for the requested session.',
            'active_session_id': active_session_id,
            'total_runs': 0,
        }

    # Group by latitude/longitude, then by zoom.
    grouped = {}
    for log in active_logs:
        lat = log.get('lat')
        lon = log.get('lon')
        zoom = log.get('zoom')

        latlon_key = f"{lat},{lon}"
        zoom_key = str(zoom)

        if latlon_key not in grouped:
            grouped[latlon_key] = {
                'lat': lat,
                'lon': lon,
                'total_runs': 0,
                'zooms': {}
            }

        if zoom_key not in grouped[latlon_key]['zooms']:
            grouped[latlon_key]['zooms'][zoom_key] = {
                'zoom': zoom,
                'count': 0,
                'avg_idle_ms': None,
                'min_idle_ms': None,
                'max_idle_ms': None,
                'runs': []
            }

        grouped[latlon_key]['total_runs'] += 1
        grouped[latlon_key]['zooms'][zoom_key]['count'] += 1
        grouped[latlon_key]['zooms'][zoom_key]['runs'].append(log)

    # Add per-zoom idle stats.
    for latlon_group in grouped.values():
        for zoom_group in latlon_group['zooms'].values():
            idle_values = [run.get('mapIdle') for run in zoom_group['runs'] if run.get('mapIdle') is not None]
            if idle_values:
                zoom_group['avg_idle_ms'] = sum(idle_values) / len(idle_values)
                zoom_group['min_idle_ms'] = min(idle_values)
                zoom_group['max_idle_ms'] = max(idle_values)

    # Keep legacy summary grouped by source/style for compatibility.
    by_source_style = {}
    for log in active_logs:
        key = f"{log.get('source', 'unknown')}_{log.get('style', 'unknown')}"
        if key not in by_source_style:
            by_source_style[key] = []
        by_source_style[key].append(log)

    summary_by_source_style = {}
    for config, items in by_source_style.items():
        idle_values = [item.get('mapIdle') for item in items if item.get('mapIdle') is not None]
        if idle_values:
            summary_by_source_style[config] = {
                'count': len(items),
                'avg_idle_ms': sum(idle_values) / len(idle_values),
                'min_idle_ms': min(idle_values),
                'max_idle_ms': max(idle_values),
            }
        else:
            summary_by_source_style[config] = {
                'count': len(items),
                'avg_idle_ms': None,
                'min_idle_ms': None,
                'max_idle_ms': None,
            }

    return {
        'grouped_by_lat_lon_zoom': grouped,
        'summary_by_source_style': summary_by_source_style,
        'active_session_id': active_session_id,
        'total_runs': len(active_logs)
    }


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
