/**
 * server.js – Local tile proxy / cache server for the Mapbox tile test.
 *
 * How it works:
 *   1. A tile request hits  GET /tiles/:z/:x/:y
 *   2. If the tile already exists in  ./tiles/  it is served from disk.
 *   3. Otherwise it is fetched from Mapbox CDN, saved to disk, then served.
 *
 * This means the first load is identical to the remote map (tiles are
 * fetched from the CDN), but every subsequent request for the same tile
 * is served instantly from the local filesystem, demonstrating the speed
 * improvement of locally cached / pre-downloaded tiles.
 *
 * Usage:
 *   MAPBOX_TOKEN=pk.eyJ1... node server.js
 *
 * The server listens on http://localhost:3000
 */

const express    = require('express');
const https      = require('https');
const fs         = require('fs');
const path       = require('path');
const rateLimit  = require('express-rate-limit');

const PORT          = process.env.PORT || 3000;
const MAPBOX_TOKEN  = process.env.MAPBOX_TOKEN || '';
const TILES_DIR     = path.join(__dirname, 'tiles');
const TILE_STYLE    = 'mapbox.satellite'; // change to any Mapbox tileset id

// Maximum zoom level supported by the tile source.
const MAX_ZOOM = 22;

const app = express();

/* ── Rate limiting (max 200 requests per minute per IP) ──────────────── */
const limiter = rateLimit({
  windowMs: 60 * 1000,
  max: 200,
  standardHeaders: true,
  legacyHeaders: false
});
app.use(limiter);

/* ── CORS ─────────────────────────────────────────────────────────────── */
app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  next();
});

/* ── Static assets: serve only index.html and the src/ directory ──────── */
app.get('/', (req, res) => res.sendFile(path.join(__dirname, 'index.html')));
app.get('/index.html', (req, res) => res.sendFile(path.join(__dirname, 'index.html')));
app.use('/src', express.static(path.join(__dirname, 'src')));
app.use('/data', express.static(path.join(__dirname, 'data')));

/* ── Ensure tiles directory exists ─────────────────────────────────────── */
fs.mkdirSync(TILES_DIR, { recursive: true });

/* ── Tile coordinate validation ─────────────────────────────────────────── */
function parseTileCoord(value) {
  if (!/^\d{1,10}$/.test(value)) return null;
  return parseInt(value, 10);
}

function isValidTileCoord(z, x, y) {
  if (z === null || x === null || y === null) return false;
  if (z < 0 || z > MAX_ZOOM) return false;
  const maxCoord = Math.pow(2, z) - 1;
  if (x < 0 || x > maxCoord) return false;
  if (y < 0 || y > maxCoord) return false;
  return true;
}

/* ── Tile proxy endpoint ────────────────────────────────────────────────── */
app.get('/tiles/:z/:x/:y', (req, res) => {
  const z = parseTileCoord(req.params.z);
  const x = parseTileCoord(req.params.x);
  const y = parseTileCoord(req.params.y);

  if (!isValidTileCoord(z, x, y)) {
    return res.status(400).send('Invalid tile coordinates');
  }

  // Build paths using validated integer values only (no user strings in paths).
  const tileDir  = path.join(TILES_DIR, String(z), String(x));
  const tilePath = path.join(tileDir, `${String(y)}.jpg`);

  // 1. Serve from disk cache if available.
  if (fs.existsSync(tilePath)) {
    console.log(`[cache hit]  z=${z} x=${x} y=${y}`);
    res.setHeader('Content-Type', 'image/jpeg');
    res.setHeader('X-Tile-Source', 'local-cache');
    return fs.createReadStream(tilePath).pipe(res);
  }

  // 2. Fetch from Mapbox CDN.
  if (!MAPBOX_TOKEN) {
    return res.status(503).json({
      error: 'MAPBOX_TOKEN environment variable not set. Start the server with MAPBOX_TOKEN=pk.eyJ1... node server.js'
    });
  }

  // Upstream URL is built entirely from validated integers + the server-side token.
  const upstreamUrl =
    `https://api.mapbox.com/v4/${TILE_STYLE}/${z}/${x}/${y}.jpg90?access_token=${MAPBOX_TOKEN}`;

  console.log(`[cache miss] z=${z} x=${x} y=${y} → fetching from CDN`);

  https.get(upstreamUrl, (upstream) => {
    if (upstream.statusCode !== 200) {
      console.error(`Mapbox returned ${upstream.statusCode} for tile z=${z} x=${x} y=${y}`);
      res.status(upstream.statusCode).send('Upstream error');
      upstream.resume();
      return;
    }

    // Stream to client and save to disk simultaneously.
    res.setHeader('Content-Type', 'image/jpeg');
    res.setHeader('X-Tile-Source', 'remote-cdn');

    fs.mkdirSync(tileDir, { recursive: true });
    const fileStream = fs.createWriteStream(tilePath);

    upstream.pipe(res);
    upstream.pipe(fileStream);
  }).on('error', (err) => {
    console.error('Error fetching tile:', err.message);
    res.status(502).send('Bad gateway');
  });
});

/* ── Start ──────────────────────────────────────────────────────────────── */
app.listen(PORT, () => {
  console.log(`\n🗺️  Mapbox tile proxy running at http://localhost:${PORT}`);
  console.log(`   Open http://localhost:${PORT}/index.html in your browser.\n`);
  if (!MAPBOX_TOKEN) {
    console.warn('⚠️  MAPBOX_TOKEN is not set. Tile caching will not work until you restart with it.\n');
  }
});
