# Mapbox tiles test (Slovenia)

This small Flask app demonstrates loading Mapbox tiles either from the remote Mapbox servers or from a local tile cache. It now supports Streets, Satellite, and 3D switching in the UI.

Files added:

- `maps_test.py` — Flask app that serves the map, local raster tiles, local satellite tiles, and local 3D style assets.
- `templates/map.html` — HTML page with Mapbox GL, style switching, and simple measurement using Resource Timing.
- `download_tiles.py` — Script to download Streets/Satellite raster tiles and a local 3D style package.
- `requirements.txt` — Python dependencies.

Quick start:

1. Install dependencies (preferably in a venv):

```bash
pip install -r requirements.txt
```

2. Set your Mapbox token:

Windows (cmd):
```cmd
set MAPBOX_TOKEN=your_token_here
```

3. (Optional) Pre-download tiles for zooms 6..18:

```bash
python download_tiles.py --style streets --min-zoom 6 --max-zoom 18
```

This downloads local Streets raster tiles into `tiles/{z}/{x}/{y}.png`.

If you only need a smaller test set, lower the zoom range. If you want the local map to look good at zoom 18, download up to 18.

Satellite tiles:

```bash
python download_tiles.py --style satellite --min-zoom 6 --max-zoom 18
```

This downloads local Satellite raster tiles into `tiles_sat/{z}/{x}/{y}.png`.

3D / vector package:

```bash
python download_tiles.py --style 3d --min-zoom 6 --max-zoom 12
```

This downloads:

- `styles/streets-v12-local.json` — the local 3D style JSON
- `sprites/` — sprite sheets used by the style
- `glyphs/` — font glyphs used by the labels
- `vectors/` — vector tiles (`.pbf`) for the vector sources referenced in the style

Use `--style 3d` if you want a local vector-backed style. Use `--style streets` or `--style satellite` if you only want raster tiles.

4. Run the Flask app:

```bash
python maps_test.py
```

5. Open the map in your browser:

- Remote tiles: `http://localhost:5000/?source=remote`
- Local tiles: `http://localhost:5000/?source=local`
- Fresh no-cache test: `http://localhost:5000/?source=remote&nocache=1` or `http://localhost:5000/?source=local&nocache=1`

In the page, use the buttons for:

- Remote / Local
- Streets / Satellite / 3D

Notes on comparison:

- Open developer tools (Network and Performance) and reload the page for accurate resource timings. The page attempts to summarise tile resource timings via the Resource Timing API and shows basic totals/averages in the bottom-left.
- The timing panel now also shows `window.load`, Mapbox `load`, Mapbox `idle`, and LCP so you can tell when the page shell is ready versus when the map has finished loading visible tiles.
- `nocache=1` disables browser caching for the app's local responses and appends cache-busting query strings to the remote tile/style requests used by the map.
- For a more reproducible benchmark, pre-download tiles and test with an empty browser cache for remote tests, and with/without local tiles for local tests.
- If you compare `http://127.0.0.1:5000/?lat=46.2&lon=14.8&zoom=18&source=remote&style=streets` with `source=local`, do not treat the timings as identical work: remote streets usually come from Mapbox's optimized hosted pipeline, while local streets here are served as raster tiles from Flask and can finish later at high zoom because there are many small requests and more bytes to transfer.

Vector tile downloads:

- The downloader already supports vector tiles for the `3d` package. Run:

```bash
python download_tiles.py --style 3d --min-zoom 6 --max-zoom 12
```

- That command downloads the 3D style JSON, sprites, glyphs, and the vector tiles needed by the vector sources referenced in the style.
- The output goes into `styles/`, `sprites/`, `glyphs/`, and `vectors/`.
- If you want to build a custom vector style later, you can reuse the downloaded `vectors/` data as the local source for that style.

Local rendering notes:

- Local Streets and Satellite are raster sources, so they need PNG/WebP/JPG tiles under `tiles/` or `tiles_sat/`.
- Local 3D is vector-based, so it needs the style JSON, glyphs, sprites, and `.pbf` vector tiles.
- The app can overzoom local raster tiles above the highest downloaded zoom, but if you want native detail at zoom 18, download the raster tiles up to 18.

Limitations and next steps:

- This example uses Mapbox tiles and style assets. Check Mapbox terms before caching tiles for production use.
- Local 3D requires the downloaded `styles/streets-v12-local.json`, matching `sprites/`, `glyphs/`, and `vectors/` assets.
- To measure perceived page load, you can automate browser loads with a headless runner (Puppeteer/Playwright) and capture timings programmatically.
