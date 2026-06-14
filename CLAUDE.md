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
app/main.py          — FastAPI app: injects LAT/LON env vars into HTML, exposes /api/sky
app/astronomy.py     — All skyfield computation: moon phase, constellation visibility, star catalog
app/skymap.py        — Pure SVG renderer: converts alt/az star positions to a 400×400 SVG
app/static/          — Frontend (index.html, style.css, app.js); served at /static
data/constellations.json  — Constellation definitions: HIP star IDs and stick-figure line segments
data/mythology.json       — Per-constellation mythology blurbs, keyed by constellation name
```

**Request flow:** Browser calls `/api/sky?lat=…&lon=…` → `main.py` calls three functions from `astronomy.py` (`get_moon_data`, `get_visible_constellations`, `get_skymap_stars`) and one from `skymap.py` (`generate_skymap`), then returns a single JSON response containing moon data, visible constellation list, SVG, and a mythology entry.

**Skyfield data:** `astronomy.py` lazy-loads two large files (`de421.bsp` ephemeris and `hip_main.dat` Hipparcos star catalog) from the path in `SKYFIELD_DATA` (defaults to `/skyfield-data`, the container path). The Dockerfile pre-downloads these at build time. For local runs outside Docker, download both files and set `SKYFIELD_DATA` to their directory. Unit tests mock all skyfield calls and do not need this.

**Test mocking:** `tests/conftest.py` patches `app.main.get_moon_data`, `app.main.get_visible_constellations`, `app.main.get_skymap_stars`, `app.main.generate_skymap`, and `app.main.pick_mythology` — i.e., names in `app.main`'s namespace. If you add new imports, patch the `app.main.*` binding, not the source module.

## Known issues / open tasks

- **Mock binding (T6.1):** `conftest.py` patches are on `app.main.*`; ensure `main.py` keeps using `from .astronomy import …` (direct name binding) so the patches stay effective. If you switch to `astronomy.get_moon_data(...)` style calls, update the patch targets to `app.astronomy.*`.
- **Constellation visibility time (D1):** The spec says "at local midnight" but `get_visible_constellations` uses `ts.now()`. This is intentional — `now` is more useful for a live sky view.
