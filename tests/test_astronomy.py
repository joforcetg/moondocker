import pytest
import app.astronomy as astro
import io

from app.astronomy import (
    phase_name_from_elongation,
    pick_default_folklore,
    pick_constellation_myth,
    polar_visibility_note,
    _date_seed,
    _build_const_lines,
    _parse_hip_catalog,
)


# ── phase_name_from_elongation ────────────────────────────────────────────────

@pytest.mark.parametrize("elongation,expected_name,expected_glyph", [
    (0.0,   "New Moon",        "🌑"),
    (10.0,  "New Moon",        "🌑"),
    (45.0,  "Waxing Crescent", "🌒"),
    (90.0,  "First Quarter",   "🌓"),
    (135.0, "Waxing Gibbous",  "🌔"),
    (180.0, "Full Moon",       "🌕"),
    (225.0, "Waning Gibbous",  "🌖"),
    (270.0, "Last Quarter",    "🌗"),
    (315.0, "Waning Crescent", "🌘"),
    (359.9, "Waning Crescent", "🌘"),
])
def test_phase_name_from_elongation(elongation, expected_name, expected_glyph):
    name, glyph = phase_name_from_elongation(elongation)
    assert name == expected_name
    assert glyph == expected_glyph


# ── polar_visibility_note ─────────────────────────────────────────────────────

def test_polar_note_does_not_set_today():
    assert polar_visibility_note("13:20", None, -5.0) == "Does not set today"


def test_polar_note_does_not_rise_today():
    assert polar_visibility_note(None, "03:09", 20.0) == "Does not rise today"


def test_polar_note_circumpolar_when_transit_above_horizon():
    assert polar_visibility_note(None, None, 12.5) == "Circumpolar (up all day)"


def test_polar_note_below_horizon_when_transit_below():
    assert polar_visibility_note(None, None, -8.0) == "Below horizon all day"


def test_polar_note_none_when_transit_unknown():
    # transit altitude could not be computed → cannot classify
    assert polar_visibility_note(None, None, None) is None


# ── pick_default_folklore ─────────────────────────────────────────────────────

_FOLK = [
    {"id": "a", "title": "A", "culture": "x", "text": "ta"},
    {"id": "b", "title": "B", "culture": "y", "text": "tb"},
    {"id": "c", "title": "C", "culture": "z", "text": "tc"},
]


def test_folklore_is_daily_deterministic():
    a = pick_default_folklore(_FOLK, date_str="2026-06-18")
    b = pick_default_folklore(_FOLK, date_str="2026-06-18")
    assert a == b
    assert a in _FOLK


def test_folklore_varies_by_date():
    days = {pick_default_folklore(_FOLK, date_str=f"2026-06-{d:02d}")["id"]
            for d in range(1, 29)}
    assert len(days) > 1  # not stuck on one entry


# ── pick_constellation_myth ───────────────────────────────────────────────────

_MYTHS = [
    {"id": "m1", "title": "M1", "text": "t1", "cast": ["Orion", "Scorpius"]},
    {"id": "m2", "title": "M2", "text": "t2", "cast": ["Scorpius"]},
    {"id": "m3", "title": "M3", "text": "t3", "cast": ["Lyra"]},
]


def test_myth_filters_by_cast_membership():
    m = pick_constellation_myth("Lyra", _MYTHS, date_str="2026-06-18")
    assert m == {"constellation": "Lyra", "title": "M3", "text": "t3"}


def test_myth_none_when_absent():
    assert pick_constellation_myth("Gemini", _MYTHS, date_str="2026-06-18") is None


def test_myth_role_ordering_lead_first():
    # Orion is lead in m1 only; pool=[m1]; Scorpius is lead in m2, second in m1
    assert pick_constellation_myth("Orion", _MYTHS, date_str="2026-06-18")["title"] == "M1"


def test_myth_role_ordering_prefers_lead():
    # Scorpius pool sorted by role: [m2 (lead), m1 (second)]; pick a date whose
    # daily index resolves to 0 and assert the lead-role myth (m2/"M2") wins.
    for d in range(1, 60):
        ds = f"2026-06-{d:02d}" if d <= 30 else f"2026-07-{d - 30:02d}"
        if _date_seed(ds) % 2 == 0:
            assert pick_constellation_myth("Scorpius", _MYTHS, date_str=ds)["title"] == "M2"
            return
    raise AssertionError("no date produced index 0")


def test_myth_is_daily_deterministic():
    a = pick_constellation_myth("Scorpius", _MYTHS, date_str="2026-06-18")
    b = pick_constellation_myth("Scorpius", _MYTHS, date_str="2026-06-18")
    assert a == b


# ── next-phase dates ──────────────────────────────────────────────────────────

def test_next_phase_dates_graceful_on_failure():
    # Bad args trip the except branch: returns all-None phases, never raises,
    # and returns a fresh copy (not the shared _EMPTY_PHASES constant).
    out = astro._next_phase_dates(None, None, None)
    assert out == astro._EMPTY_PHASES
    assert out is not astro._EMPTY_PHASES
    assert set(out) == {"next_new_date", "next_new_in_days",
                        "next_full_date", "next_full_in_days"}


# ── _build_const_lines ────────────────────────────────────────────────────────

def test_const_lines_carry_constellation_name():
    consts = [{"name": "Orion", "lines": [[1, 2], [2, 3]]}]
    hip_above = {1, 2, 3}
    lines = _build_const_lines(consts, hip_above)
    assert {"hip_a": 1, "hip_b": 2, "constellation": "Orion"} in lines
    assert all("constellation" in seg for seg in lines)


def test_const_lines_skip_below_horizon():
    consts = [{"name": "Orion", "lines": [[1, 2], [2, 9]]}]
    lines = _build_const_lines(consts, {1, 2})  # 9 missing
    assert lines == [{"hip_a": 1, "hip_b": 2, "constellation": "Orion"}]


# ── _parse_hip_catalog ────────────────────────────────────────────────────────

def _hip_row(hip, mag, ra_deg, dec_deg, extra="..."):
    """Build a pipe-delimited hip_main.dat-style row."""
    cols = ["H"] + [""] * 10
    cols[1] = f" {hip} "
    cols[5] = str(mag)
    cols[8] = str(ra_deg)
    cols[9] = str(dec_deg)
    return "|".join(cols) + "\n"


def test_parse_hip_catalog_arrays_equal_length_on_partial_failure():
    good = _hip_row(1, 6.7, 1.234, 5.678)
    bad  = _hip_row(2, "BAD", 9.0, 1.0)   # mag unparseable → whole row skipped
    hip_ids, ra_h, dec_d, mags = _parse_hip_catalog(io.StringIO(good + bad))
    assert len(hip_ids) == len(ra_h) == len(dec_d) == len(mags) == 1


def test_parse_hip_catalog_skips_short_lines():
    data = io.StringIO("H|1|too|short\n" + _hip_row(42, 5.0, 10.0, 20.0))
    hip_ids, *_ = _parse_hip_catalog(data)
    assert list(hip_ids) == [42]
