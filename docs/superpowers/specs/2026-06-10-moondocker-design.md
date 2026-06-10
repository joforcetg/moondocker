# moondocker — Design Spec

**Date:** 2026-06-10  
**Status:** Approved

---

## Overview

A single Docker container that serves a web UI showing the current moon phase, illumination, rise/set times, and a real-time night sky map with visible constellations — all computed from the user's geographic location. No external API keys. Drop-in service for `docker-compose`.

---

## Stack

| Layer | Choice |
|---|---|
| Base image | `python:3.12-slim` |
| HTTP server | FastAPI + Uvicorn (single process) |
| Astronomy | `skyfield` (moon phase, star positions, rise/set, constellation visibility) |
| Star catalog | Hipparcos (bundled with skyfield, downloaded at image build time) |
| Constellation data | Bundled `constellations.json` — per constellation: IAU name/abbr, list of HIP star pairs (line segments), list of HIP star IDs for visibility check |
| Sky map | Server-side SVG embedded in API response |
| Frontend | Static HTML/CSS/JS served by FastAPI's StaticFiles |

---

## Project Structure

```
moondocker/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── app/
    ├── main.py          # FastAPI app, mounts static files, registers routes
    ├── astronomy.py     # All skyfield computation: moon, stars, constellations, rise/set
    ├── skymap.py        # SVG sky map generator (takes computed star data, emits SVG string)
    └── static/
        ├── index.html   # Page shell with ASCII/runic chrome layout
        ├── style.css    # Monospace font, dark background, box-drawing aesthetic
        └── app.js       # Geolocation → API fetch → DOM render (no framework)
```

---

## API

### `GET /`
Returns `index.html`. The page shell with ASCII chrome and empty data slots.

### `GET /api/sky?lat={lat}&lon={lon}`
Returns JSON:

```json
{
  "moon": {
    "phase_name": "Waxing Gibbous",
    "phase_glyph": "🌔",
    "illumination_pct": 73.4,
    "rise": "14:32",
    "set": "02:17",
    "transit": "20:22"
  },
  "constellations": [
    { "name": "Orion", "abbr": "Ori", "rise": "20:11", "set": "03:44", "above_horizon": true },
    ...
  ],
  "skymap_svg": "<svg ...>...</svg>",
  "computed_at": "2026-06-10T22:00:00Z",
  "location": { "lat": 40.71, "lon": -74.01 }
}
```

The `skymap_svg` field is a self-contained SVG string the frontend injects directly into the DOM — no second request needed.

---

## Data Flow

```
Browser
  │
  ├─ navigator.geolocation.getCurrentPosition()
  │    └─ on success: lat/lon from GPS
  │    └─ on failure: lat/lon injected from LAT/LON env vars at page render time
  │
  ├─ GET /api/sky?lat=X&lon=Y
  │
FastAPI (main.py)
  │
  ├─ astronomy.py: compute moon phase, illumination, rise/set, visible constellations
  │    └─ skyfield: load Hipparcos catalog + ephemeris (de421.bsp, cached in image)
  │
  ├─ skymap.py: project visible stars to alt/az, emit SVG
  │
  └─ return JSON
  │
Browser
  └─ Renders ASCII chrome sections + injects SVG map into #skymap div
```

---

## Frontend Design

**Theme:** Monospace font (e.g. `Courier New` or `monospace`), dark background (`#0a0a0f`), dim green or amber text, Unicode box-drawing borders (`┌─┐│└─┘`).

**Layout sections (rendered as ASCII panels):**

```
┌─── ᛗᛟᛟᚾ ─────────────────────────────────────────┐
│  Phase:  Waxing Gibbous  🌔   Illumination: 73%   │
│  Rise:   14:32   Transit: 20:22   Set: 02:17       │
└────────────────────────────────────────────────────┘

┌─── ᚾᛁᚷᚺᛏ ᛋᚲᚤ ──────────────────────────────────┐
│              [SVG sky map panel]                   │
└────────────────────────────────────────────────────┘

┌─── ᚲᛟᚾᛋᛏᛖᛚᛚᚨᛏᛁᛟᚾᛋ ──────────────────────────────┐
│  Orion (Ori)     Rise 20:11  Set 03:44   ▲ ABOVE  │
│  Gemini (Gem)    Rise 19:55  Set 03:30   ▲ ABOVE  │
│  ...                                               │
└────────────────────────────────────────────────────┘
```

Rune glyphs used as section headers (ᛗᛟᛟᚾ = "MOON", ᚾᛁᚷᚺᛏ ᛋᚲᚤ = "NIGHT SKY", etc.).

**Sky map SVG design:** Dark circle (horizon mask), star dots sized by magnitude, constellation stick-figure lines in dim color, constellation name labels in a runic-adjacent small font, cardinal direction labels (N/S/E/W) around the edge. Zenith at center, horizon at edge (alt/az projection).

---

## Astronomy Computation (astronomy.py)

Using `skyfield`:

- **Moon phase:** Compute elongation between Moon and Sun → derive phase angle → map to phase name and Unicode glyph. Compute fraction illuminated.
- **Moon rise/set/transit:** `skyfield.almanac.find_risings`/`find_settings` for the current day at observer location.
- **Visible constellations:** Load the bundled constellation JSON (see below). A constellation is "visible tonight" if the average altitude of its stick-figure stars is above −10° at local midnight for the observer — accounts for partial visibility near the horizon.
- **Star positions for sky map:** For all Hipparcos stars brighter than magnitude 5.5, compute alt/az at the current time for the observer. Filter to `alt > 0` (above horizon). Pass to `skymap.py`.

---

## Sky Map SVG (skymap.py)

- Input: list of `(alt, az, magnitude, hip_id)` for visible stars + list of constellation line segments as `(hip_id_a, hip_id_b)` pairs (resolved to alt/az coords)
- Projection: `r = (90 - alt) / 90` (linear from zenith=0 to horizon=1), `x = cx + r * R * sin(az)`, `y = cy - r * R * cos(az)` — standard alt/az stereographic-ish projection
- Star size: `circle r = max(0.5, 3.5 - magnitude * 0.5)`
- Output: SVG string, fixed 400×400 viewBox, embedded directly in API response

---

## Docker

**Dockerfile:**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Pre-download skyfield data files at build time (no network at runtime)
RUN python -c "from skyfield.api import Loader; load = Loader('/skyfield-data'); load('de421.bsp'); load.open('hip_main.dat')"
COPY app/ ./app/
ENV LAT="" LON="" PORT=7432
EXPOSE 7432
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```

**docker-compose.yml:**
```yaml
services:
  moondocker:
    build: .
    ports:
      - "7432:7432"
    environment:
      LAT: ""   # fallback lat; leave blank to use browser geolocation
      LON: ""   # fallback lon
```

**LAT/LON fallback:** FastAPI reads `LAT`/`LON` env vars at startup and injects them into `index.html` as a `<script>` data block (`window.__FALLBACK__ = {lat: ..., lon: ...}`). If geolocation fails in the browser, `app.js` falls back to `window.__FALLBACK__`.

---

## Error Handling

- Geolocation denied + no env vars set → page shows a prompt asking the user to set `LAT`/`LON` env vars and restart.
- `/api/sky` called with invalid lat/lon → FastAPI returns 422 with a clear message.
- Skyfield data missing at runtime (shouldn't happen if Dockerfile is correct) → 500 with logged traceback; container logs explain the issue.
- Rise/set computation: if the moon doesn't rise or set (polar conditions) → display "Circumpolar" or "Below horizon all day" instead.

---

## Requirements

```
fastapi>=0.111
uvicorn[standard]>=0.29
skyfield>=1.49
numpy>=1.26       # skyfield dependency, pinned for reproducibility
```

---

## What Is Not In Scope

- User timezone detection (all times displayed in UTC; local time is a future enhancement)
- Planet visibility (Sun, Mars, etc.) — constellations and Moon only
- Historical or future date queries — tonight only
- Authentication or multi-user state
