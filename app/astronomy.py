import math
import hashlib
import os
from datetime import date as _date

SKYFIELD_DATA_DIR = os.environ.get("SKYFIELD_DATA", "/skyfield-data")

# Lazy-loaded skyfield globals (populated in Task 5 functions)
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
    (360.0, "Waning Crescent", "🌘"),
]


def phase_name_from_elongation(elongation: float) -> tuple[str, str]:
    """Map elongation in degrees [0, 360) to (phase_name, glyph)."""
    for threshold, name, glyph in _PHASES:
        if elongation < threshold:
            return name, glyph
    return "New Moon", "🌑"


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
    seed = int(hashlib.md5(date_str.encode()).hexdigest(), 16)

    candidates = [n for n in visible_names if n in mythology]
    if not candidates:
        candidates = list(mythology.keys())

    chosen = candidates[seed % len(candidates)]
    entries = mythology[chosen]
    entry = entries[(seed // max(len(candidates), 1)) % len(entries)]
    return {"constellation": chosen, "text": entry}
