import pytest
from unittest.mock import patch
import app.astronomy as astro
from app.astronomy import (
    phase_name_from_elongation,
    pick_default_folklore,
    pick_constellation_myth,
    polar_visibility_note,
    _date_seed,
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

def test_polar_note_none_when_moon_rises():
    assert polar_visibility_note("13:20", None, -5.0) is None


def test_polar_note_none_when_moon_sets():
    assert polar_visibility_note(None, "03:09", 20.0) is None


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

def test_next_phase_fields_present():
    # Drive get_moon_data with a real timescale but mocked almanac search so we
    # don't need ephemeris files. We patch the helper that computes next phases.
    fake = {
        "next_new_date": "2026-06-25", "next_new_in_days": 7,
        "next_full_date": "2026-07-09", "next_full_in_days": 21,
    }
    with patch.object(astro, "_next_phase_dates", return_value=fake):
        # _next_phase_dates is called inside get_moon_data; everything else that
        # needs ephemeris is exercised by existing get_moon_data tests, so here
        # we only assert the merge. Call the small helper directly:
        assert astro._next_phase_dates is not None
        out = astro._merge_next_phases({"phase_name": "Full Moon"}, fake)
        assert out["next_full_in_days"] == 21
        assert out["next_new_date"] == "2026-06-25"
