# moondocker frontend refresh — design

**Date:** 2026-06-18
**Status:** approved (design), pending implementation plan

## Summary

Full rewrite of the moondocker web frontend (`app/static/index.html`,
`style.css`, `app.js`) to polish the existing terminal aesthetic. This is an
optimization, not a redesign: the green-on-black monospace "phosphor terminal"
identity, the single-column stacked layout, and the runic panel headers all
stay. No new features, no framework, no build step, no API changes.

## Goals

- Keep the terminal identity and the `/api/sky` contract exactly as they are.
- Make the night-sky SVG the visual hero (larger, framed).
- Sharpen visual hierarchy and readability through better spacing, contrast,
  and a small palette of green shades.
- Work well on mobile (full-width sky map, scaled padding).

## Non-goals (YAGNI)

- No new features (no planets, ISS, time scrubbing, notifications).
- No JS framework, bundler, or build step — vanilla JS, served static.
- No `/api/sky` request/response changes.
- No backend / Python / Docker changes.
- No new colors beyond a single optional amber accent for the moon glyph.

## Scope

Three files rewritten:

- `app/static/index.html`
- `app/static/style.css`
- `app/static/app.js`

Everything else (FastAPI app, astronomy, skymap renderer, tests, Docker)
untouched.

## Layout — refined stack

Single column, top to bottom, wider container (~620px, was 540px) for sky-map
breathing room; full-width with scaled padding on mobile.

```
+------------------------------+
| moondocker          lat,lon  |   header strip (small, dim)
+------------------------------+
| MOON                         |
|  ) Waxing Gibbous  78% lit   |
|  rise 14:02  transit ..  set |
+------------------------------+
| NIGHT SKY                    |   <- hero: SVG fills column, framed
|   .  *   .    *   .          |
|     *  (big SVG)    *        |
|   .    *    .   *            |
+------------------------------+
| CONSTELLATIONS               |
|  > Orion   > Lyra   > Cygnus |   inline wrapping chips
+------------------------------+
| LEGEND : Orion               |
|  the hunter who...           |
+------------------------------+
```

### Components

- **Header strip:** `moondocker` wordmark + resolved `lat, lon` (dim, small).
  Coords come from whatever location actually resolved (geolocation or
  fallback).
- **MOON panel:** larger phase glyph, phase name, `NN% lit`, and the
  rise / transit / set row. When the API returns a polar `note`, show the note
  instead of the times (current behavior preserved).
- **NIGHT SKY panel (hero):** the SVG grows to fill the column up to ~520px,
  with a subtle vignette / glow frame. Injected the same safe way as today.
- **CONSTELLATIONS panel:** inline wrapping chips. `▲` marker + bright text for
  above-horizon; `▽` marker + dim text for below. Sorted above-first (kept).
  Empty list renders `none visible` (kept).
- **LEGEND panel:** mythology text; header reads `LEGEND : <constellation>`.

## Visual system (approach A — pure phosphor + amber moon accent)

- **Palette:** background `#0a0a0f`; green shades — dim `#3a5a3a`,
  mid `#6a9a6a`, bright `#9fd09f`; single accent amber `#d0a24a` used **only**
  for the moon glyph / illumination value.
- **Hierarchy:** panel headings bright, field labels dim, values mid/bright.
- **Subtle CRT treatment:** faint scanline overlay + light `text-shadow`
  phosphor glow on bright text. Kept subtle; any animation gated behind
  `prefers-reduced-motion: reduce` (no motion when the user opts out).
- Monospace throughout (current `'Courier New', Courier, monospace`).

## Data flow — unchanged

`init()` → `navigator.geolocation` → `fetchSky(lat, lon)` → `GET /api/sky?lat&lon`
→ `render(data)`.

JSON shape consumed is identical: `moon` (`phase_glyph`, `phase_name`,
`illumination_pct`, `rise`, `transit`, `set`, optional `note`), `skymap_svg`,
`constellations[]` (`name`, `abbr`, `above_horizon`), `mythology`
(`constellation`, `text`).

Renderers are refactored to emit the new markup but read the same fields. The
resolved `lat, lon` is threaded through to populate the header strip (the only
new piece of data the frontend tracks — derived from the coords already in
hand, not from the API).

SVG continues to be injected via `DOMParser` + `importNode` (not
`innerHTML` of a raw string). All user-facing strings stay escaped via `esc()`
or `textContent`.

## Loading & error states

- **Loading:** blinking-cursor status line (`locating…▊`, `fetching sky
  data…▊`); panels hidden until data arrives.
- **Geolocation denied:** fall back to env `LAT`/`LON` (`window.__FALLBACK__`);
  if none, show `location unavailable — set LAT and LON env vars and restart
  the container` (kept).
- **Server error:** red-tint status `error: <message>` (kept).
- **Empty constellations:** `none visible` (kept).

## Testing & verification

- Backend tests untouched. `/api/sky` contract is identical, so
  `tests/conftest.py` mocks remain valid.
- No JS test harness exists and none is added (YAGNI).
- Manual verification checklist:
  - Page loads and renders moon / sky / constellations / legend from a real or
    mocked `/api/sky`.
  - Geolocation-denied path falls back to `LAT`/`LON`.
  - No-fallback path shows the env-var message.
  - Server-error path shows red `error:` status.
  - Polar `note` replaces the times row.
  - Mobile width: sky map full-width, layout readable.
  - `prefers-reduced-motion` disables any animation.
- `.venv/bin/python -m pytest -v` still green (confirms nothing server-side
  broke).

## Risk

Low. Pure static asset change — no Python, API, or Docker touched.
