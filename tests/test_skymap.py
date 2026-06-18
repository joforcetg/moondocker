import pytest
from app.skymap import generate_skymap, az_alt_to_xy, star_radius, CX, CY, R


def test_zenith_star_projects_to_center():
    stars = [{"alt": 90.0, "az": 0.0, "magnitude": 1.0, "hip_id": 1}]
    svg = generate_skymap(stars, [])
    assert f'cx="{CX:.1f}" cy="{CY:.1f}"' in svg


def test_north_horizon_star_projects_to_top():
    stars = [{"alt": 0.0, "az": 0.0, "magnitude": 1.0, "hip_id": 1}]
    svg = generate_skymap(stars, [])
    expected_y = CY - R
    assert f'cy="{expected_y:.1f}"' in svg


def test_bright_star_larger_than_dim():
    # mag 0 → r=3.5; mag 5 → r=1.0
    assert star_radius(0.0) == pytest.approx(3.5)
    assert star_radius(5.0) == pytest.approx(1.0)


def test_very_dim_star_clamped_to_minimum():
    assert star_radius(10.0) == pytest.approx(0.5)


def test_empty_sky_returns_valid_svg():
    svg = generate_skymap([], [])
    assert svg.startswith("<svg")
    assert svg.strip().endswith("</svg>")


def test_constellation_line_drawn_when_both_stars_visible():
    stars = [
        {"alt": 45.0, "az": 0.0, "magnitude": 2.0, "hip_id": 1},
        {"alt": 45.0, "az": 90.0, "magnitude": 2.0, "hip_id": 2},
    ]
    lines = [{"hip_a": 1, "hip_b": 2, "constellation": "TestCon"}]
    svg = generate_skymap(stars, lines)
    assert "<line" in svg
    assert 'data-constellation="TestCon"' in svg


def test_constellation_line_omitted_when_star_missing():
    stars = [{"alt": 45.0, "az": 0.0, "magnitude": 2.0, "hip_id": 1}]
    lines = [{"hip_a": 1, "hip_b": 999, "constellation": "TestCon"}]  # hip_b not in star list
    svg = generate_skymap(stars, lines)
    assert "<line" not in svg


def test_cardinal_labels_present():
    svg = generate_skymap([], [])
    for label in ("N", "S", "E", "W"):
        assert f">{label}<" in svg


def test_lines_tagged_with_constellation():
    stars = [
        {"alt": 80, "az": 0, "magnitude": 1.0, "hip_id": 1},
        {"alt": 70, "az": 90, "magnitude": 1.0, "hip_id": 2},
        {"alt": 60, "az": 180, "magnitude": 4.0, "hip_id": 9},  # background
    ]
    lines = [{"hip_a": 1, "hip_b": 2, "constellation": "Orion"}]
    svg = generate_skymap(stars, lines)
    assert 'data-constellation="Orion"' in svg
    assert '<line' in svg and 'data-constellation="Orion"' in svg
    # figure stars (1,2) tagged; background star (9) not
    assert svg.count('class="figstar"') == 2
    assert svg.count('data-constellation') == 3  # 1 line + 2 figure stars


def test_no_constellation_attr_on_background_star():
    stars = [{"alt": 60, "az": 180, "magnitude": 4.0, "hip_id": 9}]
    svg = generate_skymap(stars, [])
    assert "data-constellation" not in svg
