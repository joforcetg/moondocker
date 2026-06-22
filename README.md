# moondocker

[![CI](https://github.com/joforcetg/moondocker/actions/workflows/ci.yml/badge.svg)](https://github.com/joforcetg/moondocker/actions/workflows/ci.yml)
[![Docker](https://ghcr-badge.egpl.dev/joforcetg/moondocker/size)](https://github.com/joforcetg/moondocker/pkgs/container/moondocker)

Self-contained Docker service — tonight's moon phase, a night sky map, and constellation myths for your location. No API keys required.

![moondocker: moon phase, night sky map, constellation myths](https://github.com/joforcetg/moondocker/raw/main/docs/screenshot.png)

## What you get

- **Moon** — phase name, SVG moon showing the lit fraction, illumination %, rise/transit/set times (UTC), next new/full moon dates
- **Night sky map** — SVG star map to magnitude 5.5 with constellation stick figures and cardinal directions; zenith at centre
- **Constellations** — 20 constellations sorted above/below horizon; clickable cards open their myth
- **Legend** — a daily dark-folklore entry by default; selecting a constellation swaps it for that constellation's myth, highlights it on the sky map, and fetches a classical artwork from Wikimedia Commons (7-day cache; graceful offline fallback)

---

## Quick start

```bash
docker run -p 7432:7432 ghcr.io/joforcetg/moondocker
```

Open [http://localhost:7432](http://localhost:7432) and grant the geolocation prompt — the sky loads for your location.

### With a fixed location

If you prefer not to use browser geolocation, or are running headless:

```bash
docker run -p 7432:7432 -e LAT=48.8566 -e LON=2.3522 ghcr.io/joforcetg/moondocker
```

---

## docker-compose

Add moondocker to your existing `docker-compose.yml`:

```yaml
services:
  moondocker:
    image: ghcr.io/joforcetg/moondocker
    restart: unless-stopped
    ports:
      - "7432:7432"
    environment:
      LAT: ""   # optional fallback latitude
      LON: ""   # optional fallback longitude
```

Or build from source instead of pulling:

```yaml
services:
  moondocker:
    build: .
    ports:
      - "7432:7432"
```

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `LAT` | _(empty)_ | Fallback latitude (decimal degrees). Used when browser geolocation is unavailable. |
| `LON` | _(empty)_ | Fallback longitude (decimal degrees). |
| `PORT` | `7432` | Port the server listens on inside the container. |

If neither browser geolocation nor `LAT`/`LON` are set, the page shows a message asking you to provide a location.

---

## VPS deploy

```bash
docker compose up -d
```

To serve under a domain with automatic HTTPS, add a [Caddyfile](https://caddyserver.com/docs/quick-starts/reverse-proxy):

```
moondocker.example.com {
    reverse_proxy localhost:7432
}
```

Then `caddy reload`.

---

## Updating

```bash
docker compose pull
docker compose up -d
```

---

<!-- ── Developer guide ───────────────────────────────────────────────────── -->

## Local development

```bash
git clone https://github.com/joforcetg/moondocker
cd moondocker
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

Download skyfield data once (required to run the app; not required for tests):

```bash
SKYFIELD_DATA=.skyfield-data .venv/bin/python -c "
from skyfield.api import Loader
from skyfield.data import hipparcos
load = Loader('.skyfield-data')
load('de421.bsp')
hipparcos.load_dataframe(load.open(hipparcos.URL))
"
```

Run tests (all skyfield calls are mocked — no data download needed):

```bash
.venv/bin/python -m pytest -v
```

Run the app:

```bash
SKYFIELD_DATA=.skyfield-data .venv/bin/python -m uvicorn app.main:app --port 7432
```

---

## Architecture

```
app/main.py          — FastAPI app: /, /api/sky, /api/myth/{constellation}, /health, /static
app/astronomy.py     — Skyfield: moon phase + dates, rise/set, constellation visibility, folklore pickers
app/skymap.py        — SVG renderer: alt/az positions → 400×400 SVG with constellation tags
app/mythart.py       — Wikimedia Commons artwork client; 7-day in-process cache
app/static/          — Frontend (index.html, style.css, app.js)
data/constellations.json  — 20 constellations: HIP star IDs and stick-figure segments
data/dark_folklore.json   — default legend pool: dark world-folklore
data/myths.json           — constellation myths with role-ordered cast
data/myth_art.json        — constellation → Wikimedia Commons category
```

`GET /api/sky?lat=…&lon=…` returns moon data, visible constellations, the SVG sky map, and a default legend in one JSON payload. `GET /api/myth/{constellation}` returns the daily myth + Wikimedia artwork (or `null`); unknown names return 404.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
