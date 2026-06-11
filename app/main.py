import os
import json
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from skyfield.api import load as skyfield_load

from .astronomy import (
    get_moon_data,
    get_visible_constellations,
    get_skymap_stars,
    pick_mythology,
)
from .skymap import generate_skymap

_ROOT      = Path(__file__).parent.parent
DATA_DIR   = _ROOT / "data"
STATIC_DIR = Path(__file__).parent / "static"

with open(DATA_DIR / "constellations.json") as _f:
    CONSTELLATION_DATA: list[dict] = json.load(_f)

with open(DATA_DIR / "mythology.json") as _f:
    MYTHOLOGY_DATA: dict[str, list[str]] = json.load(_f)

FALLBACK_LAT = os.environ.get("LAT", "")
FALLBACK_LON = os.environ.get("LON", "")

ts = skyfield_load.timescale()

app = FastAPI(title="moondocker")


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    html = (STATIC_DIR / "index.html").read_text()
    lat_val = FALLBACK_LAT if FALLBACK_LAT else "null"
    lon_val = FALLBACK_LON if FALLBACK_LON else "null"
    injection = f'<script>window.__FALLBACK__={{"lat":{lat_val},"lon":{lon_val}}}</script>'
    return html.replace("</head>", f"{injection}\n</head>")


@app.get("/api/sky")
async def get_sky(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
) -> dict:
    moon        = get_moon_data(ts, lat, lon)
    consts      = get_visible_constellations(ts, lat, lon, CONSTELLATION_DATA)
    myth        = pick_mythology([c["name"] for c in consts], MYTHOLOGY_DATA)
    stars, segs = get_skymap_stars(ts, lat, lon, CONSTELLATION_DATA)
    svg         = generate_skymap(stars, segs)

    return {
        "moon":           moon,
        "constellations": consts,
        "skymap_svg":     svg,
        "mythology":      myth,
        "location":       {"lat": lat, "lon": lon},
    }


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
