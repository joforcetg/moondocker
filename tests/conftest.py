import pytest
from unittest.mock import patch

MOCK_MOON = {
    "phase_name": "Full Moon",
    "phase_glyph": "🌕",
    "illumination_pct": 100.0,
    "rise": "18:00",
    "set": "06:00",
    "transit": "00:00",
}
MOCK_CONSTELLATIONS = [
    {"name": "Orion", "abbr": "Ori", "above_horizon": True},
    {"name": "Gemini", "abbr": "Gem", "above_horizon": True},
]
MOCK_MYTHOLOGY = {"constellation": "Orion", "text": "Orion was a hunter."}
MOCK_SVG = "<svg></svg>"


@pytest.fixture()
def client():
    with patch("app.main.get_moon_data", return_value=MOCK_MOON), \
         patch("app.main.get_visible_constellations", return_value=MOCK_CONSTELLATIONS), \
         patch("app.main.get_skymap_stars", return_value=([], [])), \
         patch("app.main.generate_skymap", return_value=MOCK_SVG), \
         patch("app.main.pick_mythology", return_value=MOCK_MYTHOLOGY):
        from fastapi.testclient import TestClient
        from app.main import app
        yield TestClient(app)
