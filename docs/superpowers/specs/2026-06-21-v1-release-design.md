# v1.0.0 Release — Design Spec

**Date:** 2026-06-21
**Status:** Approved
**Approach:** A — full README overhaul + real screenshot + feature audit + GitHub release

## Scope

Three deliverables, in order:

1. **Real screenshot** — Playwright headless capture of the running app, saved to `docs/screenshot.png`, committed.
2. **README rewrite** — same file, new structure optimised for both Docker users (above the fold) and developers (below a clear separator).
3. **v1.0.0 GitHub release** — git tag on current `main` HEAD + GitHub release with release notes.

No feature code changes. All 64 tests must still pass after every commit.

## Feature Audit (pre-release gate)

All `CLAUDE.md` goals are met. Ship is unblocked.

| Goal | Status |
|---|---|
| Browser geolocation + LAT/LON fallback | ✅ |
| Moon phase + illumination | ✅ |
| Visible constellations for location/time | ✅ |
| Web UI, no external API keys | ✅ |
| Multi-arch Docker (amd64/arm64) | ✅ |
| Health endpoint, hardened Dockerfile | ✅ |
| Deps pinned in requirements.lock (used in Dockerfile) | ✅ |
| CI: pip audit + Trivy CVE scan | ✅ |
| Mobile UI (44px targets, touch-action, iOS safe-area) | ✅ |

Known minor items — acceptable for v1 (not blocking):
- Wikimedia category correctness unverified → graceful no-image fallback, not a crash
- `moon-next` span margin asymmetry at 900px → cosmetic, pre-existing

## Screenshot

**Method:** Playwright headless (MCP plugin already active in this environment).

**Steps:**
1. Start app: `SKYFIELD_DATA=./skyfield-data LAT=48.8566 LON=2.3522 .venv/bin/python -m uvicorn app.main:app --port 7432` (Paris — reliably good constellation coverage at night).
2. Navigate to `http://localhost:7432`.
3. Wait for sky SVG to render (`#skymap svg` present).
4. Take full-page screenshot at 1280×800 (desktop viewport — shows two-column layout: moon panel + sky map on left, constellations + legend on right; all four panels visible without scrolling).
5. Save to `docs/screenshot.png`.
6. Commit: `docs: add real screenshot for README`.

If Playwright capture fails (env issue), fallback: 390×844 mobile viewport — single-column, shows moon + sky map at minimum.

## README Structure

File: `README.md` — full rewrite, same content reorganised.

```
# moondocker

[CI badge] [Docker badge]

[screenshot: docs/screenshot.png]

One-line pitch: "Self-contained Docker service — tonight's moon phase,
a night sky map, and constellation myths for your location. No API keys."

## What you get
- Moon phase name, SVG moon, illumination %, rise/transit/set times, next new/full dates
- Night sky SVG map (stars to mag 5.5, stick figures, cardinal directions)
- 20 constellations sorted above/below horizon; clickable cards for myths
- Daily folklore legend; constellation click loads myth + Wikimedia classical artwork

## Quick start
docker run -p 7432:7432 ghcr.io/joforcetg/moondocker

## With a fixed location
-e LAT=… -e LON=… explanation

## docker-compose
yaml snippet (pull from registry)
build-from-source variant

## Configuration
env var table (LAT, LON, PORT)

## VPS deploy
Caddy reverse proxy example
docker compose up -d

## Updating
docker compose pull && docker compose up -d

--- separator comment ---

## Local development
python -m venv .venv
pip install -r requirements-dev.txt
skyfield data download snippet
pytest command
uvicorn run command

## Architecture
file map table

## Contributing
link to CONTRIBUTING.md
```

**Key changes vs current README:**
- "What you get" moves above Quick start — users see the feature list before the install step.
- Screenshot is real (not a broken link).
- Dev sections (Local development, Architecture, Contributing) pushed below separator so Docker users never need to scroll there.
- Caddy example, env table, updating, architecture stay as-is (already correct content).

## GitHub Release

**Tag:** `v1.0.0` — annotated tag on current `main` HEAD after README commit.

**Release title:** `v1.0.0`

**Release notes:**

```markdown
moondocker shows tonight's moon phase, a night sky map, and constellation
myths for your location — served as a self-contained Docker image with no
external API keys required.

## What's in this release

- Moon phase, illumination, rise/transit/set times, next new/full dates
- SVG night sky map with constellation stick figures
- 20 constellations with clickable myth cards and daily-fixed legend
- Classical artwork from Wikimedia Commons (7-day cache, graceful offline)
- Mobile-optimised UI (44px touch targets, iOS safe-area insets)
- Multi-arch image: `linux/amd64` and `linux/arm64`
- Health endpoint at `/health`
- Pinned production deps (`requirements.lock`) used in Docker build
- CI: `pip audit` + Trivy CVE scan (CRITICAL/HIGH)

## Quick start

```bash
docker run -p 7432:7432 ghcr.io/joforcetg/moondocker
```

Open http://localhost:7432 — grant geolocation or pass `-e LAT=… -e LON=…`.
```

**How:** `gh release create v1.0.0 --title "v1.0.0" --notes "…"` after tag is pushed.

## What is NOT in scope

- Feature changes
- New tests
- CHANGELOG.md (single v1 release — add when v1.1 ships)
- Any changes to backend, API, or data files
