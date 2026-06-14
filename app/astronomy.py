import math
import hashlib
import logging
import os
from datetime import date as _date

logger = logging.getLogger(__name__)

SKYFIELD_DATA_DIR = os.environ.get("SKYFIELD_DATA", "/skyfield-data")

_loader = None
_eph = None
_stars_df = None

# ── Phase mapping ─────────────────────────────────────────────────────────────

_PHASES: list[tuple[float, str, str]] = [
    (22.5,  "New Moon",        "🌑"),
    (67.5,  "Waxing Crescent", "🌒"),
    (112.5, "First Quarter",   "🌓"),
    (157.5, "Waxing Gibbous",  "🌔"),
    (202.5, "Full Moon",       "🌕"),
    (247.5, "Waning Gibbous",  "🌖"),
    (292.5, "Last Quarter",    "🌗"),
    (337.5, "Waning Crescent", "🌘"),
]


def phase_name_from_elongation(elongation: float) -> tuple[str, str]:
    """Map elongation in degrees [0, 360) to (phase_name, glyph)."""
    for threshold, name, glyph in _PHASES:
        if elongation < threshold:
            return name, glyph
    return "Waning Crescent", "🌘"


# ── Mythology selection ───────────────────────────────────────────────────────

def pick_mythology(
    visible_names: list[str],
    mythology: dict[str, list[str]],
    date_str: str | None = None,
) -> dict[str, str]:
    """
    Pick one mythology entry deterministically by date.
    Candidates are filtered to visible constellations that have entries;
    falls back to the full mythology dict if none match.
    """
    if date_str is None:
        date_str = _date.today().isoformat()
    seed = int(hashlib.md5(date_str.encode(), usedforsecurity=False).hexdigest(), 16)

    candidates = [n for n in visible_names if n in mythology]
    if not candidates:
        candidates = list(mythology.keys())

    chosen = candidates[seed % len(candidates)]
    entries = mythology[chosen]
    # Use a different bit-range of the seed to avoid entropy collapse from
    # the integer division that would occur if we used seed // len(candidates).
    entry = entries[(seed >> 8) % len(entries)]
    return {"constellation": chosen, "text": entry}


# ── Skyfield lazy loaders ─────────────────────────────────────────────────────

def _get_loader():
    global _loader
    if _loader is None:
        from skyfield.api import Loader
        _loader = Loader(SKYFIELD_DATA_DIR)
    return _loader


def _get_eph():
    global _eph
    if _eph is None:
        _eph = _get_loader()("de421.bsp")
    return _eph


def _get_stars_df():
    global _stars_df
    if _stars_df is None:
        from skyfield.data import hipparcos
        with _get_loader().open("hip_main.dat") as f:
            df = hipparcos.load_dataframe(f)
        dropped = df["ra_hours"].isna() | df["dec_degrees"].isna()
        if dropped.any():
            logger.warning("dropping %d Hipparcos stars with NaN ra/dec", dropped.sum())
        _stars_df = df[~dropped]
    return _stars_df


def get_moon_data(ts, lat: float, lon: float, t=None) -> dict:
    """Return moon phase, illumination, and rise/set/transit times (UTC strings)."""
    from skyfield.api import wgs84
    from skyfield import almanac
    from skyfield.framelib import ecliptic_J2000_frame
    from skyfield.searchlib import find_maxima

    eph = _get_eph()
    if t is None:
        t = ts.now()

    # Phase angle via ecliptic longitude difference
    earth = eph["earth"]
    e = earth.at(t)
    moon_ecl = e.observe(eph["moon"]).apparent().frame_latlon(ecliptic_J2000_frame)
    sun_ecl  = e.observe(eph["sun"]).apparent().frame_latlon(ecliptic_J2000_frame)
    elongation = (moon_ecl[1].degrees - sun_ecl[1].degrees) % 360
    illumination = round((1 - math.cos(math.radians(elongation))) / 2 * 100, 1)
    phase_name, phase_glyph = phase_name_from_elongation(elongation)

    location = wgs84.latlon(lat, lon)
    # Search from UTC midnight today so we capture a moonrise that already happened
    utc_dt = t.utc_datetime()
    t0 = ts.from_datetime(utc_dt.replace(hour=0, minute=0, second=0, microsecond=0))
    t1 = ts.tt_jd(t0.tt + 1.0)
    rise_str = set_str = transit_str = None

    try:
        f = almanac.risings_and_settings(eph, eph["moon"], location)
        times, events = almanac.find_discrete(t0, t1, f)
        for t_evt, evt in zip(times, events):
            if evt == 1 and rise_str is None:
                rise_str = t_evt.utc_strftime("%H:%M")
            elif evt == 0 and set_str is None:
                set_str = t_evt.utc_strftime("%H:%M")
    except Exception:
        logger.exception("moon rise/set lookup failed (lat=%s lon=%s)", lat, lon)

    try:
        observer = earth + location

        def _moon_alt(t_inner):
            alt, _, _ = observer.at(t_inner).observe(eph["moon"]).apparent().altaz()
            return alt.degrees

        _moon_alt.rough_period = 1.0  # Moon transits ~once per diurnal day
        transit_times, _ = find_maxima(t0, t1, _moon_alt)
        if len(transit_times) > 0:
            transit_str = transit_times[0].utc_strftime("%H:%M")
    except Exception:
        logger.exception("moon transit lookup failed (lat=%s lon=%s)", lat, lon)

    return {
        "phase_name":       phase_name,
        "phase_glyph":      phase_glyph,
        "illumination_pct": illumination,
        "rise":             rise_str,
        "set":              set_str,
        "transit":          transit_str,
    }


def get_visible_constellations(
    ts, lat: float, lon: float, constellation_data: list[dict], t=None
) -> list[dict]:
    """
    Return constellations whose average stick-figure star altitude > -10°.
    above_horizon is True if at least one defining star is above 0°.
    """
    from skyfield.api import wgs84, Star

    eph = _get_eph()
    stars_df = _get_stars_df()
    observer = eph["earth"] + wgs84.latlon(lat, lon)
    if t is None:
        t = ts.now()

    # Collect all unique HIP IDs across all constellations, then do a single
    # vectorized observation instead of one Skyfield call per star.
    all_hip_ids = sorted({
        hip_id
        for const in constellation_data
        for hip_id in const["hip_ids"]
        if hip_id in stars_df.index
    })

    if not all_hip_ids:
        return []

    batch_df = stars_df.loc[all_hip_ids]
    stars_obj = Star.from_dataframe(batch_df)
    alt_arr, _, _ = observer.at(t).observe(stars_obj).apparent().altaz()
    hip_alt: dict[int, float] = {
        int(hip_id): float(a)
        for hip_id, a in zip(all_hip_ids, alt_arr.degrees)
    }

    visible = []
    for const in constellation_data:
        alts = [hip_alt[h] for h in const["hip_ids"] if h in hip_alt]
        if alts and (sum(alts) / len(alts)) > -10.0:
            visible.append({
                "name":          const["name"],
                "abbr":          const["abbr"],
                "above_horizon": any(a > 0 for a in alts),
            })
    return visible


def get_skymap_stars(
    ts, lat: float, lon: float, constellation_data: list[dict], t=None
) -> tuple[list[dict], list[dict]]:
    """
    Return (star_list, const_lines) for sky map rendering.
    star_list:   [{"alt", "az", "magnitude", "hip_id"}, ...]  — above horizon, mag ≤ 5.5
    const_lines: [{"hip_a", "hip_b"}, ...]  — only segments where both stars are above horizon
    """
    from skyfield.api import wgs84, Star

    eph = _get_eph()
    stars_df = _get_stars_df()
    observer = eph["earth"] + wgs84.latlon(lat, lon)
    if t is None:
        t = ts.now()

    bright = stars_df[stars_df["magnitude"] <= 5.5]
    stars_obj = Star.from_dataframe(bright)
    astrometric = observer.at(t).observe(stars_obj)
    alt_arr, az_arr, _ = astrometric.apparent().altaz()

    star_list: list[dict] = []
    hip_above: set[int] = set()

    for i, (hip_id, row) in enumerate(bright.iterrows()):
        a = float(alt_arr.degrees[i])
        z = float(az_arr.degrees[i])
        if a > 0:
            star_list.append({
                "alt":       a,
                "az":        z,
                "magnitude": float(row["magnitude"]),
                "hip_id":    int(hip_id),
            })
            hip_above.add(int(hip_id))

    const_lines: list[dict] = []
    for const in constellation_data:
        for hip_a, hip_b in const["lines"]:
            if hip_a in hip_above and hip_b in hip_above:
                const_lines.append({"hip_a": hip_a, "hip_b": hip_b})

    return star_list, const_lines
