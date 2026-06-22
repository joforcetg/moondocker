from tests.conftest import MOCK_MOON, MOCK_LEGEND, MOCK_SVG
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
    assert data["legend"]["title"] == "The Wendigo"
    assert "mythology" not in data
    assert data["location"] == {"lat": 40.71, "lon": -74.01}
    assert data["computed_at"].endswith("Z")


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


def test_sky_returns_legend_and_has_myth():
    from tests.conftest import MOCK_MOON, MOCK_LEGEND, MOCK_SVG

    def _fake_pick(name, myths, date_str=None):
        return {"constellation": name, "title": "M", "text": "t"} if name == "Orion" else None

    with patch("app.main.get_moon_data", return_value=MOCK_MOON), \
         patch("app.main.get_visible_constellations", return_value=[
             {"name": "Orion", "abbr": "Ori", "above_horizon": True},
             {"name": "Gemini", "abbr": "Gem", "above_horizon": True},
         ]), \
         patch("app.main.get_skymap_stars", return_value=([], [])), \
         patch("app.main.generate_skymap", return_value=MOCK_SVG), \
         patch("app.main.pick_default_folklore", return_value=MOCK_LEGEND), \
         patch("app.main.pick_constellation_myth", side_effect=_fake_pick):
        from fastapi.testclient import TestClient
        from app.main import app
        c = TestClient(app)
        r = c.get("/api/sky?lat=40&lon=-74")
    assert r.status_code == 200
    body = r.json()
    assert "legend" in body and "mythology" not in body
    assert body["legend"]["title"] == "The Wendigo"
    has = {entry["name"]: entry["has_myth"] for entry in body["constellations"]}
    assert has["Orion"] is True and has["Gemini"] is False


def test_myth_endpoint_ok():
    art = {"url": "u", "title": "t", "author": "a", "license": "PD", "credit_url": "c"}
    with patch("app.main.pick_constellation_myth",
               return_value={"constellation": "Orion", "title": "M", "text": "t"}), \
         patch("app.main.get_constellation_art", return_value=art):
        from fastapi.testclient import TestClient
        from app.main import app
        c = TestClient(app)
        r = c.get("/api/myth/Orion")
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "M" and body["image"]["license"] == "PD"


def test_myth_endpoint_unknown_404():
    from fastapi.testclient import TestClient
    from app.main import app
    r = TestClient(app).get("/api/myth/NotAConstellation")
    assert r.status_code == 404


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_security_headers(client):
    r = client.get("/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]
