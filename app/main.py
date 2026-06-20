import os
import json
import logging
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from skyfield.api import load as skyfield_load

from .astronomy import (
    get_moon_data,
    get_visible_constellations,
    get_skymap_stars,
    pick_default_folklore,
    pick_constellation_myth,
)
from .skymap import generate_skymap
from .mythart import get_constellation_art

logger = logging.getLogger(__name__)

_ROOT      = Path(__file__).parent.parent
DATA_DIR   = _ROOT / "data"
STATIC_DIR = Path(__file__).parent / "static"

with open(DATA_DIR / "constellations.json") as _f:
    CONSTELLATION_DATA: list[dict] = json.load(_f)
with open(DATA_DIR / "dark_folklore.json", encoding="utf-8") as _f:
    FOLKLORE_DATA: list[dict] = json.load(_f)
with open(DATA_DIR / "myths.json", encoding="utf-8") as _f:
    MYTHS_DATA: list[dict] = json.load(_f)
with open(DATA_DIR / "myth_art.json", encoding="utf-8") as _f:
    MYTH_ART_DATA: dict[str, dict] = json.load(_f)

CONSTELLATION_NAMES = {c["name"] for c in CONSTELLATION_DATA}


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


@app.get("/health")
def health():
    return {"status": "ok"}


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
    for c in consts:
        c["has_myth"] = pick_constellation_myth(c["name"], MYTHS_DATA) is not None
    legend      = pick_default_folklore(FOLKLORE_DATA)
    stars, segs = get_skymap_stars(ts, lat, lon, CONSTELLATION_DATA, t=t)
    svg         = generate_skymap(stars, segs)

    return {
        "moon":           moon,
        "constellations": consts,
        "skymap_svg":     svg,
        "legend":         legend,
        "computed_at":    t.utc_iso(),
        "location":       {"lat": lat, "lon": lon},
    }


@app.get("/api/myth/{constellation}")
async def get_myth(constellation: str) -> dict:
    if constellation not in CONSTELLATION_NAMES:
        raise HTTPException(status_code=404, detail="unknown constellation")
    myth = pick_constellation_myth(constellation, MYTHS_DATA)
    image = None
    art_cfg = MYTH_ART_DATA.get(constellation)
    if art_cfg:
        image = get_constellation_art(constellation, art_cfg["category"])
    return {
        "constellation": constellation,
        "title": myth["title"] if myth else None,
        "text":  myth["text"] if myth else None,
        "image": image,
    }


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
