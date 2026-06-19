import json
import logging
import random
import re
import time
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "moondocker/1.0 (+https://github.com/joforcetg/moondocker)"
TIMEOUT = 5.0
CACHE_TTL_SECONDS = 7 * 24 * 3600

_CACHE: dict[str, tuple[float, dict]] = {}


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.load(resp)


def _api(params: dict) -> dict:
    params = {**params, "format": "json"}
    return _get_json(API + "?" + urllib.parse.urlencode(params))


_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".tif", ".tiff")


def _image_titles(titles: list[str]) -> list[str]:
    return [t for t in titles if t.lower().endswith(_IMAGE_EXTS)]


def _category_titles(category: str) -> list[str]:
    members = _api({
        "action": "query", "list": "categorymembers",
        "cmtitle": category, "cmtype": "file", "cmlimit": "100",
    }).get("query", {}).get("categorymembers", [])
    return _image_titles([m.get("title", "") for m in members])


def _search_titles(name: str) -> list[str]:
    """Fallback when a configured category is wrong/empty: search Commons files
    by constellation name, biased toward artwork."""
    results = _api({
        "action": "query", "list": "search",
        "srsearch": f"{name} mythology", "srnamespace": "6", "srlimit": "40",
    }).get("query", {}).get("search", [])
    return _image_titles([r.get("title", "") for r in results])


def _image_from_titles(titles: list[str]) -> dict | None:
    """Batch-query candidates, return the first that carries a real image url."""
    sample = random.sample(titles, min(15, len(titles)))
    pages = _api({
        "action": "query", "prop": "imageinfo", "titles": "|".join(sample),
        "iiprop": "url|extmetadata",
    }).get("query", {}).get("pages", {})
    candidates = list(pages.values())
    random.shuffle(candidates)
    for page in candidates:
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("url")
        if not url:
            continue
        ext = info.get("extmetadata", {})
        title = page.get("title") or url.rsplit("/", 1)[-1]
        return {
            "url": url,
            "title": title.removeprefix("File:"),
            "author": _strip(ext.get("Artist", {}).get("value", "")),
            "license": ext.get("LicenseShortName", {}).get("value", ""),
            "credit_url": info.get("descriptionurl", ""),
        }
    return None


def _fetch_art(category: str, name: str | None = None) -> dict | None:
    """
    Find a usable image for a constellation. Tries the configured category
    first; if that is empty/wrong, falls back to a name search on Commons so a
    bad category no longer blanks the panel. None on any problem.
    """
    try:
        titles = _category_titles(category)
        art = _image_from_titles(titles) if titles else None
        if art is None and name:
            stitles = _search_titles(name)
            if stitles:
                art = _image_from_titles(stitles)
        return art
    except Exception:
        logger.exception("Wikimedia art fetch failed for %s", category)
        return None


def _strip(html: str) -> str:
    """Crude tag strip — Artist value is often wrapped in <a>…</a>."""
    return re.sub(r"<[^>]+>", "", html).strip()


def get_constellation_art(name: str, category: str) -> dict | None:
    cached = _CACHE.get(name)
    if cached and (time.time() - cached[0]) < CACHE_TTL_SECONDS:
        return cached[1]
    art = _fetch_art(category, name)
    if art is not None:
        _CACHE[name] = (time.time(), art)
    return art
