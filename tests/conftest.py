import pytest
from unittest.mock import patch

MOCK_MOON = {
    "phase_name": "Full Moon",
    "phase_glyph": "🌕",
    "illumination_pct": 100.0,
    "rise": "18:00",
    "set": "06:00",
    "transit": "00:00",
    "note": None,
}
MOCK_LEGEND = {"id": "x", "title": "The Wendigo", "culture": "Algonquian", "text": "..."}
MOCK_SVG = "<svg></svg>"


@pytest.fixture()
def client():
    with patch("app.main.get_moon_data", return_value=MOCK_MOON), \
         patch("app.main.get_visible_constellations", return_value=[
             {"name": "Orion", "abbr": "Ori", "above_horizon": True},
             {"name": "Gemini", "abbr": "Gem", "above_horizon": True},
         ]), \
         patch("app.main.get_skymap_stars", return_value=([], [])), \
         patch("app.main.generate_skymap", return_value=MOCK_SVG), \
         patch("app.main.pick_default_folklore", return_value=MOCK_LEGEND):
        from fastapi.testclient import TestClient
        from app.main import app
        yield TestClient(app)
