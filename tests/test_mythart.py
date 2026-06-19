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


def test_fetch_art_skips_nonimage_and_urlless(monkeypatch):
    # A .pdf is filtered out before query; a urlless file is skipped for the
    # candidate that actually carries an image url. (The reliability fix.)
    members = {"query": {"categorymembers": [
        {"title": "File:Doc.pdf"},
        {"title": "File:Bad.jpg"},
        {"title": "File:Good.png"},
    ]}}
    info = {"query": {"pages": {
        "1": {"title": "File:Bad.jpg", "imageinfo": [{}]},          # no url
        "2": {"title": "File:Good.png", "imageinfo": [{
            "url": "https://upload.wikimedia.org/Good.png",
            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Good.png",
            "extmetadata": {"LicenseShortName": {"value": "CC0"}},
        }]},
    }}}
    calls = iter([members, info])
    monkeypatch.setattr(ma, "_get_json", lambda url: next(calls))
    out = ma._fetch_art("Category:Mixed")
    assert out is not None
    assert out["url"].endswith("Good.png")
    assert out["license"] == "CC0"


def test_fetch_art_falls_back_to_search(monkeypatch):
    # Empty/wrong category → search Commons by name instead of blanking.
    empty_cat = {"query": {"categorymembers": []}}
    search = {"query": {"search": [{"title": "File:Lyra art.jpg"}]}}
    info = {"query": {"pages": {"3": {"title": "File:Lyra art.jpg", "imageinfo": [{
        "url": "https://upload.wikimedia.org/Lyra.jpg",
        "descriptionurl": "https://commons.wikimedia.org/wiki/File:Lyra art.jpg",
        "extmetadata": {"LicenseShortName": {"value": "Public domain"}},
    }]}}}}
    calls = iter([empty_cat, search, info])
    monkeypatch.setattr(ma, "_get_json", lambda url: next(calls))
    out = ma._fetch_art("Category:Empty", "Lyra")
    assert out is not None
    assert out["url"].endswith("Lyra.jpg")


def test_falls_back_to_alt_category(monkeypatch):
    empty_cat = {"query": {"categorymembers": []}}
    alt_members = {"query": {"categorymembers": [{"title": "File:Good.jpg"}]}}
    info = {"query": {"pages": {"1": {"title": "File:Good.jpg", "imageinfo": [{
        "url": "https://upload.wikimedia.org/Good.jpg",
        "descriptionurl": "https://commons.wikimedia.org/wiki/File:Good.jpg",
        "extmetadata": {"LicenseShortName": {"value": "Public domain"}},
    }]}}}}
    calls = iter([empty_cat, alt_members, info])
    monkeypatch.setattr(ma, "_get_json", lambda url: next(calls))
    out = ma._fetch_art("Category:Empty", "Orion", alt_categories=["Category:AltCat"])
    assert out is not None
    assert out["url"].endswith("Good.jpg")


def test_falls_back_to_search_terms(monkeypatch):
    empty_cat = {"query": {"categorymembers": []}}
    search = {"query": {"search": [{"title": "File:Star.jpg"}]}}
    info = {"query": {"pages": {"2": {"title": "File:Star.jpg", "imageinfo": [{
        "url": "https://upload.wikimedia.org/Star.jpg",
        "descriptionurl": "https://commons.wikimedia.org/wiki/File:Star.jpg",
        "extmetadata": {"LicenseShortName": {"value": "CC0"}},
    }]}}}}
    calls = iter([empty_cat, search, info])
    monkeypatch.setattr(ma, "_get_json", lambda url: next(calls))
    out = ma._fetch_art("Category:Empty", "Orion", search_terms=["Orion engraving art"])
    assert out is not None
    assert out["url"].endswith("Star.jpg")


def test_falls_back_to_generic_search(monkeypatch):
    empty_cat = {"query": {"categorymembers": []}}
    search = {"query": {"search": [{"title": "File:Generic.jpg"}]}}
    info = {"query": {"pages": {"3": {"title": "File:Generic.jpg", "imageinfo": [{
        "url": "https://upload.wikimedia.org/Generic.jpg",
        "descriptionurl": "https://commons.wikimedia.org/wiki/File:Generic.jpg",
        "extmetadata": {"LicenseShortName": {"value": "PD"}},
    }]}}}}
    calls = iter([empty_cat, search, info])
    monkeypatch.setattr(ma, "_get_json", lambda url: next(calls))
    out = ma._fetch_art("Category:Empty", "Orion")
    assert out is not None
    assert out["url"].endswith("Generic.jpg")


def test_falls_back_to_atlas_search(monkeypatch):
    empty_cat = {"query": {"categorymembers": []}}
    empty_search = {"query": {"search": []}}
    atlas_search = {"query": {"search": [{"title": "File:Atlas.jpg"}]}}
    info = {"query": {"pages": {"4": {"title": "File:Atlas.jpg", "imageinfo": [{
        "url": "https://upload.wikimedia.org/Atlas.jpg",
        "descriptionurl": "https://commons.wikimedia.org/wiki/File:Atlas.jpg",
        "extmetadata": {"LicenseShortName": {"value": "PD"}},
    }]}}}}
    # category empty + generic search empty + Uranometria hits
    calls = iter([empty_cat, empty_search, atlas_search, info])
    monkeypatch.setattr(ma, "_get_json", lambda url: next(calls))
    out = ma._fetch_art("Category:Empty", "Orion")
    assert out is not None
    assert out["url"].endswith("Atlas.jpg")


def test_all_strategies_exhausted_returns_none(monkeypatch):
    empty_cat = {"query": {"categorymembers": []}}
    empty_search = {"query": {"search": []}}
    # 1 category + generic search + 3 atlas searches = 5 empty responses
    calls = iter([empty_cat, empty_search, empty_search, empty_search, empty_search])
    monkeypatch.setattr(ma, "_get_json", lambda url: next(calls))
    out = ma._fetch_art("Category:Empty", "Orion")
    assert out is None


def test_get_constellation_art_reads_alt_categories_from_myth_art(monkeypatch):
    """get_constellation_art passes alt_categories and search_terms from _MYTH_ART."""
    fake_myth_art = {"Orion": {
        "category": "Category:Orion in art",
        "alt_categories": ["Category:AltOrion"],
        "search_terms": ["orion art"],
    }}
    payload = {"url": "u", "title": "t", "author": "a", "license": "PD", "credit_url": "c"}
    monkeypatch.setattr(ma, "_MYTH_ART", fake_myth_art)
    with patch.object(ma, "_fetch_art", return_value=payload) as mock_fetch:
        ma._CACHE.clear()
        result = ma.get_constellation_art("Orion", "Category:Orion in art")
    mock_fetch.assert_called_once_with(
        "Category:Orion in art", "Orion",
        ["Category:AltOrion"], ["orion art"]
    )
    assert result == payload
