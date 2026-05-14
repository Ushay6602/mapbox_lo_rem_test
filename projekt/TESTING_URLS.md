# Performance Testing - URL Parameter Guide

The map now supports URL parameters for automated performance testing. Use query parameters to test different configurations.

## URL Parameters

- `lat` - Latitude (decimal, default: 46.07)
- `lon` - Longitude (decimal, default: 14.55)  
- `zoom` - Zoom level (0-18, default: 7)
- `source` - Connection mode: `remote` or `local` (default: remote)
- `style` - Tile style: `streets`, `satellite`, or `3d` (default: streets)

## Test Examples

### Basic Ljubljana Streets (Remote)
```
http://localhost:5000/?lat=46.07&lon=14.55&zoom=10&source=remote&style=streets
```

### Local Ljubljana Streets Test
```
http://localhost:5000/?lat=46.07&lon=14.55&zoom=10&source=local&style=streets
```

### Remote Satellite at Higher Zoom
```
http://localhost:5000/?lat=46.56&lon=14.99&zoom=12&source=remote&style=satellite
```

### Southwest Slovenia (Krško) - Local Streets
```
http://localhost:5000/?lat=45.96&lon=15.43&zoom=10&source=local&style=streets
```

### Northeast (Maribor) - Remote Satellite
```
http://localhost:5000/?lat=46.56&lon=15.64&zoom=11&source=remote&style=satellite
```

### Low Zoom (National View)
```
http://localhost:5000/?lat=46.15&lon=14.99&zoom=7&source=remote&style=streets
```

### High Zoom (City Detail)
```
http://localhost:5000/?lat=46.07&lon=14.55&zoom=15&source=remote&style=streets
```

## Performance Metrics Displayed

For each test configuration, the page shows:
- **Test Configuration**: Zoom level and coordinates
- **Mode**: Remote (Mapbox API) or Local (filesystem)
- **Style**: Streets, Satellite, or 3D
- **Tiles Loaded**: Number of tiles for current view
- **Total Time**: Total milliseconds to load all tiles
- **Avg Time**: Average milliseconds per tile
- **Min/Max**: Fastest and slowest individual tile loads

## Test Scenarios

### Scenario 1: Same Location, Different Zoom Levels
Compare loading times for same coordinates at different detail levels:
- `?lat=46.07&lon=14.55&zoom=8&source=remote&style=streets`
- `?lat=46.07&lon=14.55&zoom=10&source=remote&style=streets`
- `?lat=46.07&lon=14.55&zoom=12&source=remote&style=streets`

### Scenario 2: Remote vs Local Comparison
Test the same location with both connection modes:
- `?lat=46.07&lon=14.55&zoom=10&source=remote&style=streets` (Remote)
- `?lat=46.07&lon=14.55&zoom=10&source=local&style=streets` (Local)

### Scenario 3: Style Performance
Compare loading times across different styles:
- `?lat=46.07&lon=14.55&zoom=10&source=remote&style=streets` (Streets)
- `?lat=46.07&lon=14.55&zoom=10&source=remote&style=satellite` (Satellite)

### Scenario 4: Geographical Variation
Test different regions of Slovenia:
- Ljubljana (center): `lat=46.07&lon=14.55`
- Maribor (NE): `lat=46.56&lon=15.64`
- Krško (SE): `lat=45.96&lon=15.43`
- Kranjska Gora (NW): `lat=46.39&lon=13.98`

## Notes

- **Local tiles**: Only works if downloaded. Use `download_tiles.py` first:
  ```bash
  python projekt/download_tiles.py --style streets --min-zoom 8 --max-zoom 12
  ```
  
- **Satellite tiles**: Requires separate download:
  ```bash
  python projekt/download_tiles.py --style satellite --min-zoom 8 --max-zoom 12
  ```

- **3D tiles**: Requires 3D package download (deferred):
  ```bash
  python projekt/download_tiles.py --style 3d --min-zoom 8 --max-zoom 12
  ```

- Performance times are measured using browser Resource Timing API and reflect actual network/filesystem latency
