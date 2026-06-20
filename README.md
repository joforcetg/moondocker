# moondocker

[![CI](https://github.com/joforcetg/moondocker/actions/workflows/test.yml/badge.svg)](https://github.com/joforcetg/moondocker/actions/workflows/test.yml)
[![Docker](https://ghcr-badge.egpl.dev/joforcetg/moondocker/size)](https://github.com/joforcetg/moondocker/pkgs/container/moondocker)

A self-contained Docker service that displays tonight's moon phase, a night sky map, and the constellations visible from your current location — no external API keys required.

![moondocker panels: moon phase, night sky SVG map, constellation list, folklore legend](https://github.com/joforcetg/moondocker/raw/main/docs/screenshot.png)

---

## Quick start

```bash
docker run -p 7432:7432 ghcr.io/joforcetg/moondocker
```

Open [http://localhost:7432](http://localhost:7432). The page asks for browser geolocation permission and fetches your local sky.

### With a location fallback

If you prefer not to use browser geolocation, or are running headless:

```bash
docker run -p 7432:7432 -e LAT=38.7169 -e LON=-9.1399 ghcr.io/joforcetg/moondocker
```

---

## docker-compose

Add moondocker as a service in your existing `docker-compose.yml`:

```yaml
services:
  moondocker:
    image: ghcr.io/joforcetg/moondocker
    ports:
      - "7432:7432"
    environment:
      LAT: ""   # optional fallback latitude
      LON: ""   # optional fallback longitude
```

Or build from source:

```yaml
services:
  moondocker:
    build: .
    ports:
      - "7432:7432"
    environment:
      LAT: ""
      LON: ""
```

---

## VPS deploy

```bash
# pull and start in background
docker compose up -d
```

To put it behind a domain with automatic HTTPS, add a [Caddyfile](https://caddyserver.com/docs/quick-starts/reverse-proxy):

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

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `LAT` | _(empty)_ | Fallback latitude (decimal degrees). Used when browser geolocation is unavailable. |
| `LON` | _(empty)_ | Fallback longitude (decimal degrees). |
| `PORT` | `7432` | Port the server listens on inside the container. |

If neither browser geolocation nor `LAT`/`LON` are available, the page shows a message asking you to set the env vars and restart.

---

## What it shows

- **Moon** — phase name, an SVG-rendered moon showing the lit fraction, illumination %, today's rise / transit / set times (UTC), and the dates of the next new and full moon. At polar latitudes where the moon never crosses the horizon, it shows "Circumpolar" or "Below horizon all day" instead.
- **Night sky map** — SVG projection of stars brighter than magnitude 5.5 with constellation stick figures, cardinal directions, and zenith at center. Each segment is tagged with its constellation so clicking a card can highlight it.
- **Constellations** — list of 20 constellations sorted by whether they are above the horizon (▲) or rising/setting (▽). Cards with a myth are clickable.
- **Legend** — by default, a daily rotation of dark world-folklore, seeded by date (same entry for all users on the same day). Clicking a constellation card swaps it for a daily-fixed myth featuring that constellation, highlights the figure in the sky map, and loads a classical artwork from Wikimedia Commons (cached 7 days; the page works fine offline without it).

---

## Building from source

```bash
git clone https://github.com/joforcetg/moondocker
cd moondocker
docker build -t moondocker .
docker run -p 7432:7432 moondocker
```

The Dockerfile pre-downloads the Hipparcos star catalog and the DE421 ephemeris (~68 MB total) at build time so the container runs fully offline.

---

## Local development

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt

# Download skyfield data once
SKYFIELD_DATA=.skyfield-data .venv/bin/python -c "
from skyfield.api import Loader
from skyfield.data import hipparcos
load = Loader('.skyfield-data')
load('de421.bsp')
hipparcos.load_dataframe(load.open(hipparcos.URL))
"

# Run tests (no skyfield data needed — all skyfield calls are mocked)
.venv/bin/python -m pytest -v

# Run the app
SKYFIELD_DATA=.skyfield-data .venv/bin/python -m uvicorn app.main:app --port 7432
```

---

## Architecture

```
app/main.py          — FastAPI app: serves /, /api/sky, /api/myth/{constellation}, and /static
app/astronomy.py     — Skyfield computation: moon phase + next-phase dates, rise/set, constellation visibility, folklore/myth pickers
app/skymap.py        — SVG renderer: alt/az star positions → 400×400 SVG, tagged with data-constellation
app/mythart.py       — Wikimedia Commons artwork client with a 7-day cache (stdlib urllib; only network path)
app/static/          — Frontend (index.html, style.css, app.js)
data/constellations.json  — 20 constellations: HIP star IDs and stick-figure lines
data/dark_folklore.json   — default-legend pool: dark world-folklore, not constellation-tied
data/myths.json           — constellation myths with role-ordered cast
data/myth_art.json        — constellation → Wikimedia Commons category
```

`GET /api/sky?lat=…&lon=…` returns a single JSON payload with moon data (incl. next-phase dates), visible constellations (each flagged `has_myth`), the SVG sky map, and a `legend` (the default folklore entry). The browser makes one request and renders everything client-side. Clicking a constellation card then calls `GET /api/myth/{constellation}`, which returns the daily myth plus a Wikimedia artwork (or `null`); unknown names return 404. Only this endpoint touches the network — `/api/sky` is fully offline-capable.
