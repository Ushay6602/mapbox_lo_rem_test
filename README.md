# mapbox_lo_rem_test

A side-by-side performance comparison of **locally cached** Mapbox tiles versus
**remotely fetched** Mapbox CDN tiles.  The goal is to measure the real-world
speed improvement that a local tile cache (or pre-downloaded tile archive) gives
you, as a first step toward optimising a Mapbox-based application.

---

## Project structure

```
mapbox_lo_rem_test/
├── index.html            # Side-by-side map UI
├── server.js             # Local tile proxy / cache server (Express)
├── package.json
├── src/
│   └── map.js            # Mapbox GL JS initialisation & performance tracking
└── data/
    ├── sample_points.geojson   # Starter dataset (5 world cities)
    └── README.md               # Guide for adding your own geodata
```

---

## Quick start

### 1 — Install dependencies

```bash
npm install
```

### 2 — Start the local tile server

```bash
MAPBOX_TOKEN=pk.eyJ1… node server.js
```

Replace `pk.eyJ1…` with your own
[Mapbox public access token](https://account.mapbox.com/access-tokens/).

The server starts at **http://localhost:3000**.

### 3 — Open the app

Navigate to **http://localhost:3000/index.html**, paste your Mapbox token into
the input box, and click **Load Maps**.

The left panel loads tiles from the Mapbox CDN; the right panel loads the same
tiles through the local cache proxy.  Both maps stay in sync as you pan and
zoom.  Load times and tile counts are displayed at the bottom of the page.

---

## How the local tile cache works

```
Browser ──► GET /tiles/z/x/y ──► server.js
                                      │
                              tile on disk?
                             yes ──► serve from ./tiles/
                             no  ──► fetch from api.mapbox.com
                                         │
                                    save to disk
                                         │
                                    serve to browser
```

On the first page load, tiles are fetched from Mapbox (identical to the remote
map).  On every subsequent load the cached tiles are served from the local
filesystem, eliminating network latency.

---

## Adding your own geodata

Drop files into the `data/` folder and load them in `src/map.js` as an
additional layer.  See [`data/README.md`](data/README.md) for supported formats
and instructions for large tile archives.

---

## Uploading this project with GitHub Copilot in VS Code

If you want to use **GitHub Copilot** (or the Copilot coding agent) from
VS Code to help you upload or extend this project, open the Copilot Chat panel
and use one of the following prompts depending on what you need:

### Upload / push all project files to GitHub

```
@workspace I want to commit and push all project files to GitHub.
Please help me:
1. Stage everything with `git add .`
2. Check what is excluded by .gitignore (node_modules, tiles/, *.mbtiles)
3. Commit with message "Add full project structure for Mapbox tile test"
4. Push to origin main
```

### Upload a large tile file with Git LFS

```
@workspace I have a large .mbtiles file I want to add to the repository.
Please help me set up Git LFS, track *.mbtiles files, and then commit and
push the file to GitHub.
```

### Add a new geodata layer to the map

```
@workspace I have a GeoJSON file at data/my_data.geojson.
Please add it as a new vector layer on both maps in src/map.js,
using a circle paint style with colour #e94560.
```

### Extend the performance stats

```
@workspace Please add a "bytes transferred" metric to the stats bar
in index.html and track it in src/map.js by listening to the
XMLHttpRequest or fetch requests made by Mapbox GL JS.
```

---

## License

MIT
