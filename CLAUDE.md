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

## Design

The UI follows an **ASCII / runic aesthetic**: monospace fonts, Unicode box-drawing characters, rune-like glyphs, dark background, minimal color (think terminal / ancient script). This theme applies to all visual elements — moon phase display, sky map, constellation labels, and layout chrome.

## Architecture (planned)

- **Single container** — one `Dockerfile`, one process (or small process supervisor if needed)
- **Backend** — computes astronomy data (moon phase, constellation visibility, rise/set times) using a library like `ephem` (Python), `astronomia` (Node), or similar; exposes a small HTTP API
- **Frontend** — static HTML/CSS/JS served by the backend; uses the browser Geolocation API to get lat/lon, then fetches data from the backend; renders in the ASCII/runic style
- **docker-compose integration** — the image should work as a drop-in service block; default port is `7432` (chosen to avoid common-port conflicts); accepts `LAT` / `LON` env vars as a fallback when geolocation is unavailable

## Commands

> Populate once the stack is chosen.

```bash
# Build
docker build -t moondocker .

# Run standalone
docker run -p 7432:7432 moondocker

# Run with explicit location fallback
docker run -p 7432:7432 -e LAT=40.7128 -e LON=-74.0060 moondocker

# Compose
docker compose up
```
