import pytest
from app.astronomy import (
    phase_name_from_elongation,
    pick_mythology,
    pick_default_folklore,
    pick_constellation_myth,
    polar_visibility_note,
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


# ── pick_mythology ────────────────────────────────────────────────────────────

MYTH = {
    "Orion":  ["Orion fact A", "Orion fact B"],
    "Leo":    ["Leo fact A"],
    "Gemini": ["Gemini fact A", "Gemini fact B"],
}


def test_mythology_restricts_to_visible_constellations():
    result = pick_mythology(["Orion"], MYTH, date_str="2026-01-01")
    assert result["constellation"] == "Orion"


def test_mythology_falls_back_when_no_visible_match():
    result = pick_mythology([], MYTH, date_str="2026-01-01")
    assert result["constellation"] in MYTH


def test_mythology_falls_back_when_visible_have_no_entry():
    result = pick_mythology(["Taurus"], MYTH, date_str="2026-01-01")
    assert result["constellation"] in MYTH


def test_mythology_is_deterministic_for_same_date():
    r1 = pick_mythology(["Orion", "Leo", "Gemini"], MYTH, date_str="2026-06-10")
    r2 = pick_mythology(["Orion", "Leo", "Gemini"], MYTH, date_str="2026-06-10")
    assert r1 == r2


def test_mythology_result_has_required_keys():
    result = pick_mythology(["Orion"], MYTH, date_str="2026-06-10")
    assert "constellation" in result
    assert "text" in result
    assert isinstance(result["text"], str)
    assert len(result["text"]) > 0


def test_mythology_text_belongs_to_chosen_constellation():
    result = pick_mythology(["Orion", "Leo"], MYTH, date_str="2026-06-10")
    expected_texts = MYTH[result["constellation"]]
    assert result["text"] in expected_texts


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


def test_myth_is_daily_deterministic():
    a = pick_constellation_myth("Scorpius", _MYTHS, date_str="2026-06-18")
    b = pick_constellation_myth("Scorpius", _MYTHS, date_str="2026-06-18")
    assert a == b
