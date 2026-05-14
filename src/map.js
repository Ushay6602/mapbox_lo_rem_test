/**
 * map.js – Side-by-side Mapbox performance comparison: remote vs local tiles.
 *
 * Remote map: uses the standard Mapbox CDN (api.mapbox.com).
 * Local map:  uses a tile proxy served from the local Express server
 *             (see server.js).  Falls back gracefully when the local
 *             server is not running.
 *
 * Metrics collected per map:
 *   • Total load time   (ms from map init → "idle" event)
 *   • Tile request count
 */

/* ── helpers ─────────────────────────────────────────────────────────── */

function log(msg) {
  document.getElementById('log').textContent = msg;
  console.log('[map.js]', msg);
}

function buildMapboxStyle(token, tileUrlTemplate) {
  return {
    version: 8,
    sources: {
      'raster-tiles': {
        type: 'raster',
        tiles: [tileUrlTemplate],
        tileSize: 256,
        attribution: '© <a href="https://www.mapbox.com/">Mapbox</a>'
      }
    },
    layers: [
      {
        id: 'simple-tiles',
        type: 'raster',
        source: 'raster-tiles',
        minzoom: 0,
        maxzoom: 22
      }
    ]
  };
}

/* ── metrics tracking ─────────────────────────────────────────────────── */

function trackMap(map, timeEl, tileCountEl, label) {
  const start = performance.now();
  let tileCount = 0;

  map.on('dataloading', (e) => {
    if (e.dataType === 'tile') {
      tileCount += 1;
      tileCountEl.textContent = tileCount;
    }
  });

  map.once('idle', () => {
    const elapsed = Math.round(performance.now() - start);
    timeEl.textContent = elapsed;
    log(`${label} map idle after ${elapsed} ms (${tileCount} tiles).`);
  });
}

/* ── main entry point ─────────────────────────────────────────────────── */

function initMaps() {
  const token = document.getElementById('mb-token').value.trim();
  if (!token || !token.startsWith('pk.')) {
    alert('Please enter a valid Mapbox public token (starts with pk.)');
    return;
  }

  mapboxgl.accessToken = token;

  const CENTER = [0, 20];
  const ZOOM   = 2;

  /* ── Remote map ─── */
  const remoteMap = new mapboxgl.Map({
    container: 'map-remote',
    style: buildMapboxStyle(
      token,
      `https://api.mapbox.com/v4/mapbox.satellite/{z}/{x}/{y}.jpg90?access_token=${token}`
    ),
    center: CENTER,
    zoom: ZOOM
  });
  remoteMap.addControl(new mapboxgl.NavigationControl(), 'top-right');
  trackMap(
    remoteMap,
    document.getElementById('remote-time'),
    document.getElementById('remote-tiles'),
    'Remote'
  );

  /* ── Local map ─── */
  const localMap = new mapboxgl.Map({
    container: 'map-local',
    style: buildMapboxStyle(
      token,
      // The Express tile proxy (server.js) forwards requests to Mapbox and
      // serves them from disk on subsequent requests.
      `http://localhost:3000/tiles/{z}/{x}/{y}`
    ),
    center: CENTER,
    zoom: ZOOM,
    transformRequest: (url) => {
      // Keep access token only for direct Mapbox calls, not for local proxy.
      return { url };
    }
  });
  localMap.addControl(new mapboxgl.NavigationControl(), 'top-right');
  trackMap(
    localMap,
    document.getElementById('local-time'),
    document.getElementById('local-tiles'),
    'Local'
  );

  /* ── Sync viewports ─── */
  function syncFrom(source, target) {
    source.on('move', () => {
      target.jumpTo({
        center: source.getCenter(),
        zoom:   source.getZoom(),
        bearing: source.getBearing(),
        pitch:   source.getPitch()
      });
    });
  }
  syncFrom(remoteMap, localMap);
  syncFrom(localMap,  remoteMap);

  log('Maps initialised — panning or zooming will sync both views.');
}
