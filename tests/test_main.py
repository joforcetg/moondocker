from tests.conftest import MOCK_MOON, MOCK_CONSTELLATIONS, MOCK_MYTHOLOGY, MOCK_SVG
from unittest.mock import patch


def test_root_returns_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_root_html_contains_fallback_script(client):
    resp = client.get("/")
    assert "window.__FALLBACK__" in resp.text


def test_sky_api_success(client):
    resp = client.get("/api/sky?lat=40.71&lon=-74.01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["moon"]["phase_name"] == "Full Moon"
    assert isinstance(data["constellations"], list)
    assert data["skymap_svg"] == MOCK_SVG
    assert data["mythology"]["constellation"] == "Orion"
    assert data["location"] == {"lat": 40.71, "lon": -74.01}


def test_sky_api_rejects_invalid_lat(client):
    resp = client.get("/api/sky?lat=999&lon=0")
    assert resp.status_code == 422


def test_sky_api_rejects_invalid_lon(client):
    resp = client.get("/api/sky?lat=0&lon=999")
    assert resp.status_code == 422


def test_sky_api_rejects_missing_params(client):
    resp = client.get("/api/sky")
    assert resp.status_code == 422


def test_static_css_served(client):
    resp = client.get("/static/style.css")
    assert resp.status_code == 200


def test_static_js_served(client):
    resp = client.get("/static/app.js")
    assert resp.status_code == 200
