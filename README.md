# moondocker

A self-contained Docker service that displays tonight's moon phase, a night sky map, and the constellations visible from your current location — no external API keys required.

![moondocker panels: moon phase, night sky SVG map, constellation list, mythology](https://github.com/joforcetg/moondocker/raw/main/docs/screenshot.png)

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

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `LAT` | _(empty)_ | Fallback latitude (decimal degrees). Used when browser geolocation is unavailable. |
| `LON` | _(empty)_ | Fallback longitude (decimal degrees). |
| `PORT` | `7432` | Port the server listens on inside the container. |

If neither browser geolocation nor `LAT`/`LON` are available, the page shows a message asking you to set the env vars and restart.

---

## What it shows

- **Moon** — phase name, Unicode glyph, illumination %, and today's rise / transit / set times (UTC).
- **Night sky map** — SVG projection of stars brighter than magnitude 5.5 with constellation stick figures, cardinal directions, and zenith at center.
- **Constellations** — list of 20 constellations sorted by whether they are above the horizon (▲) or rising/setting (▽).
- **Mythology** — a daily rotation of mythology entries, seeded by date (same entry for all users on the same day).

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
app/main.py          — FastAPI app: serves /, /api/sky, and /static
app/astronomy.py     — Skyfield computation: moon phase, rise/set, constellation visibility
app/skymap.py        — SVG renderer: alt/az star positions → 400×400 SVG
app/static/          — Frontend (index.html, style.css, app.js)
data/constellations.json  — 20 constellations: HIP star IDs and stick-figure lines
data/mythology.json       — Mythology blurbs per constellation
```

`GET /api/sky?lat=…&lon=…` returns a single JSON payload with moon data, visible constellations, the SVG sky map, and a mythology entry. The browser makes one request and renders everything client-side.
