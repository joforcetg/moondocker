# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**moondocker** is a self-contained Docker service that displays tonight's moon phase, a night sky map, and the constellations visible from the user's current geographic location. It is designed to be imported into a `docker-compose.yml` as a single service.

## Goal

Produce a Docker image that:
- Accepts the user's location (via browser geolocation or env-var lat/lon fallback)
- Computes the current moon phase and illumination
- Renders visible constellations for that location and date/time
- Serves everything as a web UI (no external API keys required if possible)

## Commands

All Python commands must use `.venv/bin/python` — the system Python lacks the project's dependencies.

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

**Request flow:** Browser calls `/api/sky?lat=…&lon=…` → `main.py` calls three functions from `astronomy.py` (`get_moon_data`, `get_visible_constellations`, `get_skymap_stars`), one from `skymap.py` (`generate_skymap`), and `pick_default_folklore`; it returns a single JSON response with moon data (incl. next-phase dates), the visible-constellation list (each tagged `has_myth`), the SVG, and a `legend` entry (default folklore). Clicking a constellation card calls `GET /api/myth/{constellation}` → daily-fixed myth + live/cached Wikimedia artwork (`image`, or `null`); unknown names return 404.

**Skyfield data:** `astronomy.py` lazy-loads two large files (`de421.bsp` ephemeris and `hip_main.dat` Hipparcos star catalog) from the path in `SKYFIELD_DATA` (defaults to `/skyfield-data`, the container path). The Dockerfile pre-downloads these at build time. For local runs outside Docker, download both files and set `SKYFIELD_DATA` to their directory. Unit tests mock all skyfield calls and do not need this.

**Test mocking:** `tests/conftest.py` patches `app.main.get_moon_data`, `app.main.get_visible_constellations`, `app.main.get_skymap_stars`, `app.main.generate_skymap`, and `app.main.pick_default_folklore` — i.e., names in `app.main`'s namespace. Tests that exercise `/api/myth` patch `app.main.pick_constellation_myth` and `app.main.get_constellation_art`. If you add new imports, patch the `app.main.*` binding, not the source module.

## Known issues / open tasks

- **Mock binding (T6.1):** `conftest.py` patches are on `app.main.*` (e.g. `app.main.pick_default_folklore`, `app.main.pick_constellation_myth`, `app.main.get_constellation_art`); ensure `main.py` keeps using `from .astronomy import …` / `from .mythart import …` (direct name binding) so the patches stay effective. If you switch to `astronomy.get_moon_data(...)` style calls, update the patch targets to `app.astronomy.*`.
- **Constellation visibility time (D1):** The spec says "at local midnight" but `get_visible_constellations` uses `ts.now()`. This is intentional — `now` is more useful for a live sky view.
