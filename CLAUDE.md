# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repo.

## Project

**moondocker** — self-contained Docker service. Shows tonight's moon phase, night sky map, constellations visible from user's location. Import into `docker-compose.yml` as single service.

## Goal

Docker image that:
- Accepts user location (browser geolocation or env-var lat/lon fallback)
- Computes moon phase + illumination
- Renders visible constellations for that location + date/time
- Serves as web UI (no external API keys if possible)

## Commands

All Python commands use `.venv/bin/python` — system Python lacks project deps.

```bash
# Run all tests
.venv/bin/python -m pytest -v

# Run a single test file
.venv/bin/python -m pytest tests/test_main.py -v

# Run a single test by name
.venv/bin/python -m pytest tests/test_astronomy.py::test_phase_name_from_elongation -v

# Run the app locally (requires skyfield data — see Architecture below)
SKYFIELD_DATA=/path/to/local/skyfield-data .venv/bin/python -m uvicorn app.main:app --port 7432

# Build and run via Docker
docker build -t moondocker .
docker run -p 7432:7432 moondocker

# Run with explicit location fallback
docker run -p 7432:7432 -e LAT=40.7128 -e LON=-74.0060 moondocker

# Compose
docker compose up
```

## Architecture

```
app/main.py          — FastAPI app: injects LAT/LON env vars into HTML, exposes /api/sky and /api/myth/{constellation}
app/astronomy.py     — All skyfield computation: moon phase (+ next new/full dates), constellation visibility, star catalog, folklore/myth pickers
app/skymap.py        — Pure SVG renderer: converts alt/az star positions to a 400×400 SVG, tags segments with data-constellation
app/mythart.py       — Wikimedia Commons artwork client with a 7-day in-process cache (stdlib urllib; network only)
app/static/          — Frontend (index.html, style.css, app.js); served at /static
data/constellations.json  — Constellation definitions: HIP star IDs and stick-figure line segments
data/dark_folklore.json   — Default-legend pool: dark world-folklore, not constellation-tied
data/myths.json           — Constellation myths with role-ordered cast (constellation names)
data/myth_art.json        — Constellation → Wikimedia Commons category for artwork lookup
```

**Request flow:** Browser → `/api/sky?lat=…&lon=…` → `main.py` calls `get_moon_data`, `get_visible_constellations`, `get_skymap_stars` (from `astronomy.py`), `generate_skymap` (from `skymap.py`), `pick_default_folklore`; returns JSON: moon data (incl. next-phase dates), visible-constellation list (each tagged `has_myth`), SVG, `legend` (default folklore). Constellation card click → `GET /api/myth/{constellation}` → daily-fixed myth + live/cached Wikimedia artwork (`image` or `null`); unknown names 404.

**Skyfield data:** `astronomy.py` lazy-loads `de421.bsp` (ephemeris) + `hip_main.dat` (Hipparcos catalog) from `SKYFIELD_DATA` (defaults to `/skyfield-data`). Dockerfile pre-downloads at build time. Local runs: download both files, set `SKYFIELD_DATA` to their dir. Unit tests mock all skyfield calls — no data needed.

**Test mocking:** `tests/conftest.py` patches `app.main.get_moon_data`, `app.main.get_visible_constellations`, `app.main.get_skymap_stars`, `app.main.generate_skymap`, `app.main.pick_default_folklore` — names in `app.main` namespace. `/api/myth` tests patch `app.main.pick_constellation_myth` + `app.main.get_constellation_art`. New imports: patch `app.main.*` binding, not source module.

## Known issues / open tasks

- **Mock binding (T6.1):** `conftest.py` patches on `app.main.*` (e.g. `app.main.pick_default_folklore`, `app.main.pick_constellation_myth`, `app.main.get_constellation_art`); keep `main.py` using `from .astronomy import …` / `from .mythart import …` (direct name binding) for patches to work. Switch to `astronomy.get_moon_data(...)` style → update patch targets to `app.astronomy.*`.
- **Constellation visibility time (D1):** Spec says "at local midnight" but `get_visible_constellations` uses `ts.now()`. Intentional — `now` more useful for live sky view.
