# data/

This folder holds geographic data files used by the map application.

## Files included

| File | Description |
|------|-------------|
| `sample_points.geojson` | Five world cities as GeoJSON point features (included as a starter dataset) |

## Adding your own data

You can drop any of the following file types here and the app will be able
to reference them:

| Format | Extension | Notes |
|--------|-----------|-------|
| GeoJSON | `.geojson` / `.json` | Best for small-to-medium vector datasets |
| CSV with lat/lon | `.csv` | Convert to GeoJSON first with tools like **csv2geojson** |
| Shapefile | `.shp` + companions | Convert to GeoJSON with **ogr2ogr** or **mapshaper** |

## Large raster tile files

Raster tile archives (`.mbtiles`, `.pmtiles`) are **excluded from Git** via
`.gitignore` because they can be many gigabytes in size.

To share them with your team use one of:
- **Git LFS** – `git lfs track "*.mbtiles"` then commit normally.
- **Cloud storage** – upload to S3 / GCS and reference the URL in the app.
- **Tile hosting services** – Mapbox Studio, TileServer GL, or Martin.

Place any `.mbtiles` / `.pmtiles` file in this folder and update `server.js`
to serve tiles from it using a library such as
[`@mapbox/mbtiles`](https://github.com/mapbox/node-mbtiles).
