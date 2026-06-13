import os
import json
import logging
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

logger = logging.getLogger(__name__)

_ROOT      = Path(__file__).parent.parent
DATA_DIR   = _ROOT / "data"
STATIC_DIR = Path(__file__).parent / "static"

with open(DATA_DIR / "constellations.json") as _f:
    CONSTELLATION_DATA: list[dict] = json.load(_f)

with open(DATA_DIR / "mythology.json") as _f:
    MYTHOLOGY_DATA: dict[str, list[str]] = json.load(_f)


def _parse_coord(val: str) -> float | None:
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


FALLBACK_LAT = _parse_coord(os.environ.get("LAT", ""))
FALLBACK_LON = _parse_coord(os.environ.get("LON", ""))

ts = skyfield_load.timescale()

app = FastAPI(title="moondocker")

# Pre-render the index page once at startup. FALLBACK coords are env-var
# constants that never change while the process is running, so there is no
# reason to re-read the file or rebuild the script on every request.
_lat_js = str(FALLBACK_LAT) if FALLBACK_LAT is not None else "null"
_lon_js = str(FALLBACK_LON) if FALLBACK_LON is not None else "null"
_fallback_script = (
    f'<script>window.__FALLBACK__={{"lat":{_lat_js},"lon":{_lon_js}}}</script>'
)
_raw_html = (STATIC_DIR / "index.html").read_text()
_INDEX_HTML = _raw_html.replace("</head>", f"{_fallback_script}\n</head>", 1)
if _INDEX_HTML == _raw_html:
    logger.warning("index.html has no </head> tag — window.__FALLBACK__ was not injected")


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return _INDEX_HTML


@app.get("/api/sky")
async def get_sky(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
) -> dict:
    t           = ts.now()
    moon        = get_moon_data(ts, lat, lon, t=t)
    consts      = get_visible_constellations(ts, lat, lon, CONSTELLATION_DATA, t=t)
    myth        = pick_mythology([c["name"] for c in consts], MYTHOLOGY_DATA)
    stars, segs = get_skymap_stars(ts, lat, lon, CONSTELLATION_DATA, t=t)
    svg         = generate_skymap(stars, segs)

    return {
        "moon":           moon,
        "constellations": consts,
        "skymap_svg":     svg,
        "mythology":      myth,
        "location":       {"lat": lat, "lon": lon},
    }


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
