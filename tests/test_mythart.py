import pytest
import time
from unittest.mock import patch
import app.mythart as ma


@pytest.fixture(autouse=True)
def _clear_cache():
    ma._CACHE.clear()
    yield
    ma._CACHE.clear()


def test_returns_fetch_result_and_caches():
    payload = {"url": "u", "title": "t", "author": "a", "license": "PD", "credit_url": "c"}
    with patch.object(ma, "_fetch_art", return_value=payload) as fake:
        a = ma.get_constellation_art("Orion", "Category:Orion in art")
        b = ma.get_constellation_art("Orion", "Category:Orion in art")
    assert a == payload and b == payload
    assert fake.call_count == 1  # second call served from cache


def test_failure_returns_none_and_not_cached():
    with patch.object(ma, "_fetch_art", return_value=None) as fake:
        assert ma.get_constellation_art("Orion", "cat") is None
        assert ma.get_constellation_art("Orion", "cat") is None
    assert fake.call_count == 2  # not cached → refetched


def test_stale_cache_refetches():
    payload = {"url": "u", "title": "t", "author": "a", "license": "PD", "credit_url": "c"}
    ma._CACHE["Orion"] = (time.time() - ma.CACHE_TTL_SECONDS - 1, payload)
    with patch.object(ma, "_fetch_art", return_value=payload) as fake:
        ma.get_constellation_art("Orion", "cat")
    assert fake.call_count == 1


def test_fetch_art_parses_api(monkeypatch):
    members = {"query": {"categorymembers": [{"title": "File:Orion.jpg"}]}}
    info = {"query": {"pages": {"7": {"imageinfo": [{
        "url": "https://upload.wikimedia.org/Orion.jpg",
        "descriptionurl": "https://commons.wikimedia.org/wiki/File:Orion.jpg",
        "extmetadata": {
            "Artist": {"value": "Johannes Hevelius"},
            "LicenseShortName": {"value": "Public domain"},
        },
    }]}}}}
    calls = iter([members, info])
    monkeypatch.setattr(ma, "_get_json", lambda url: next(calls))
    out = ma._fetch_art("Category:Orion in art")
    assert out["url"].endswith("Orion.jpg")
    assert out["author"] == "Johannes Hevelius"
    assert out["license"] == "Public domain"
    assert out["credit_url"].endswith("File:Orion.jpg")


def test_fetch_art_empty_category(monkeypatch):
    monkeypatch.setattr(ma, "_get_json", lambda url: {"query": {"categorymembers": []}})
    assert ma._fetch_art("Category:Empty") is None
