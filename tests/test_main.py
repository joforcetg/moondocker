import inspect
import json
from pathlib import Path
from urllib.parse import urlparse
from tests.conftest import MOCK_MOON, MOCK_LEGEND, MOCK_SVG
from unittest.mock import patch, MagicMock
import pytest
import app.main as _main

DATA = Path(__file__).parent.parent / "data"


@pytest.fixture(autouse=True)
def _clear_sky_cache():
    _main._compute_sky.cache_clear()
    yield
    _main._compute_sky.cache_clear()


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


def test_static_fonts_cached_immutable(client):
    r = client.get("/static/fonts/noto-sans-runic-runic-400-normal.woff2")
    assert r.status_code == 200
    cc = r.headers.get("cache-control", "")
    assert "immutable" in cc and "max-age=31536000" in cc


def test_static_js_cached_short(client):
    r = client.get("/static/app.js")
    cc = r.headers.get("cache-control", "")
    assert "public" in cc and "max-age=3600" in cc


def test_api_no_cache_header(client):
    r = client.get("/api/sky?lat=40&lon=-74")
    assert "cache-control" not in r.headers


# --- performance tests ---

def test_sky_gzipped(client):
    big_svg = "<svg>" + ("x" * 600) + "</svg>"
    with patch("app.main.generate_skymap", return_value=big_svg):
        r = client.get("/api/sky?lat=40.71&lon=-74.01",
                       headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200
    assert r.headers.get("content-encoding") == "gzip"
    assert r.json()["skymap_svg"] == big_svg  # TestClient auto-decompresses


def test_small_body_not_gzipped(client):
    r = client.get("/health", headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200
    assert "gzip" not in r.headers.get("content-encoding", "")


def test_sky_route_is_sync():
    assert not inspect.iscoroutinefunction(_main.get_sky)
    assert not inspect.iscoroutinefunction(_main.get_myth)


def test_sky_cache_hits(client):
    mock_skymap = MagicMock(return_value=MOCK_SVG)
    with patch("app.main.generate_skymap", mock_skymap):
        client.get("/api/sky?lat=40.71&lon=-74.01")
        client.get("/api/sky?lat=40.71&lon=-74.01")
    assert mock_skymap.call_count == 1  # second call served from cache


# --- text accuracy ---

def test_myth_text_matches_data():
    myths = json.loads((DATA / "myths.json").read_text(encoding="utf-8"))
    consts = {c["name"] for c in json.loads((DATA / "constellations.json").read_text())}
    # all myth titles/texts keyed by constellation
    myth_titles = {m["title"] for m in myths if any(n in consts for n in m["cast"])}

    with patch("app.main.get_constellation_art", return_value=None):
        from fastapi.testclient import TestClient
        from app.main import app
        r = TestClient(app).get("/api/myth/Orion")
    assert r.status_code == 200
    body = r.json()
    # returned title must exist somewhere in the real data (daily-fixed pick)
    assert body["title"] in myth_titles
    assert body["text"]  # non-empty text


# --- image accuracy ---

def test_myth_image_shape():
    art = {
        "url": "https://upload.wikimedia.org/wikipedia/commons/Orion.jpg",
        "title": "Orion the Hunter",
        "author": "Johannes Hevelius",
        "license": "Public domain",
        "credit_url": "https://commons.wikimedia.org/wiki/File:Orion.jpg",
    }
    with patch("app.main.pick_constellation_myth",
               return_value={"constellation": "Orion", "title": "T", "text": "t"}), \
         patch("app.main.get_constellation_art", return_value=art):
        from fastapi.testclient import TestClient
        from app.main import app
        r = TestClient(app).get("/api/myth/Orion")
    assert r.status_code == 200
    img = r.json()["image"]
    assert set(img) >= {"url", "title", "author", "license", "credit_url"}
    parsed = urlparse(img["url"])
    assert parsed.scheme == "https" and parsed.netloc == "upload.wikimedia.org"
