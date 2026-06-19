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


def polar_visibility_note(
    rise: str | None, set_: str | None, transit_alt: float | None
) -> str | None:
    """
    Classify the moon when it neither rises nor sets in the search window.

    At high latitudes the moon can stay above (circumpolar) or below the horizon
    for the whole day, so there is no rise/set event. The transit (highest point)
    altitude distinguishes the two. Returns None when a normal rise or set exists.
    """
    if rise is None and set_ is None and transit_alt is not None:
        return "Circumpolar (up all day)" if transit_alt > 0 else "Below horizon all day"
    return None


# ── Mythology selection ───────────────────────────────────────────────────────

def _date_seed(date_str: str | None) -> int:
    if date_str is None:
        date_str = _date.today().isoformat()
    return int(hashlib.md5(date_str.encode(), usedforsecurity=False).hexdigest(), 16)


def pick_default_folklore(folklore: list[dict], date_str: str | None = None) -> dict:
    """Pick one dark-folklore entry deterministically by date."""
    seed = _date_seed(date_str)
    return folklore[seed % len(folklore)]


def pick_constellation_myth(
    name: str, myths: list[dict], date_str: str | None = None
) -> dict | None:
    """
    Pick one myth that features `name`, deterministically by date.
    Eligible pool = myths whose cast contains `name`, ordered by the role
    `name` plays (lead first, then second, then third). Returns None if `name`
    is in no myth's cast.
    """
    pool = [m for m in myths if name in m["cast"]]
    if not pool:
        return None
    pool.sort(key=lambda m: m["cast"].index(name))
    seed = _date_seed(date_str)
    chosen = pool[seed % len(pool)]
    return {"constellation": name, "title": chosen["title"], "text": chosen["text"]}


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


_EMPTY_PHASES = {
    "next_new_date": None, "next_new_in_days": None,
    "next_full_date": None, "next_full_in_days": None,
}


def _next_phase_dates(ts, eph, t) -> dict:
    """Next New (event 0) and Full (event 2) moon after t, via skyfield almanac."""
    from skyfield import almanac
    try:
        t1 = ts.tt_jd(t.tt + 40.0)  # one synodic month fits in 40 days
        f = almanac.moon_phases(eph)
        times, events = almanac.find_discrete(t, t1, f)
        out = dict(_EMPTY_PHASES)
        today = t.utc_datetime().date()
        for t_evt, evt in zip(times, events):
            d = t_evt.utc_datetime().date()
            days = (d - today).days
            if evt == 0 and out["next_new_date"] is None:
                out["next_new_date"], out["next_new_in_days"] = d.isoformat(), days
            elif evt == 2 and out["next_full_date"] is None:
                out["next_full_date"], out["next_full_in_days"] = d.isoformat(), days
        return out
    except Exception:
        logger.exception("next moon-phase lookup failed")
        return dict(_EMPTY_PHASES)


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

    transit_alt = None
    try:
        observer = earth + location

        def _moon_alt(t_inner):
            alt, _, _ = observer.at(t_inner).observe(eph["moon"]).apparent().altaz()
            return alt.degrees

        _moon_alt.rough_period = 1.0  # Moon transits ~once per diurnal day
        transit_times, _ = find_maxima(t0, t1, _moon_alt)
        if len(transit_times) > 0:
            transit_str = transit_times[0].utc_strftime("%H:%M")
            transit_alt = float(_moon_alt(transit_times[0]))
    except Exception:
        logger.exception("moon transit lookup failed (lat=%s lon=%s)", lat, lon)

    result = {
        "phase_name":       phase_name,
        "phase_glyph":      phase_glyph,
        "illumination_pct": illumination,
        "rise":             rise_str,
        "set":              set_str,
        "transit":          transit_str,
        "note":             polar_visibility_note(rise_str, set_str, transit_alt),
    }
    result.update(_next_phase_dates(ts, eph, t))
    return result


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


def _build_const_lines(constellation_data: list[dict], hip_above: set[int]) -> list[dict]:
    """Line segments [{hip_a, hip_b, constellation}] for segments with both stars above horizon."""
    lines = []
    for const in constellation_data:
        for hip_a, hip_b in const["lines"]:
            if hip_a in hip_above and hip_b in hip_above:
                lines.append({"hip_a": hip_a, "hip_b": hip_b, "constellation": const["name"]})
    return lines


def get_skymap_stars(
    ts, lat: float, lon: float, constellation_data: list[dict], t=None
) -> tuple[list[dict], list[dict]]:
    """
    Return (star_list, const_lines) for sky map rendering.
    star_list:   [{"alt", "az", "magnitude", "hip_id"}, ...]  — above horizon, mag ≤ 5.5
    const_lines: [{"hip_a", "hip_b", "constellation"}, ...]  — only segments where both stars are above horizon
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

    # Vectorized filter to stars above the horizon. iterrows() is row-by-row
    # Python and dominates this call for the ~1300 bright stars; numpy masking
    # over the already-computed alt/az arrays is the same result, far faster.
    alts = alt_arr.degrees
    azs = az_arr.degrees
    hip_ids = bright.index.to_numpy()
    mags = bright["magnitude"].to_numpy()
    above_mask = alts > 0

    star_list: list[dict] = [
        {
            "alt":       float(a),
            "az":        float(z),
            "magnitude": float(m),
            "hip_id":    int(h),
        }
        for a, z, m, h in zip(
            alts[above_mask], azs[above_mask], mags[above_mask], hip_ids[above_mask]
        )
    ]
    hip_above: set[int] = {int(h) for h in hip_ids[above_mask]}

    const_lines = _build_const_lines(constellation_data, hip_above)

    return star_list, const_lines
