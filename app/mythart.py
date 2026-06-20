import json
import logging
import random
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "moondocker/1.0 (+https://github.com/joforcetg/moondocker)"
TIMEOUT = 5.0
CACHE_TTL_SECONDS = 7 * 24 * 3600

_CACHE: dict[str, tuple[float, dict]] = {}

_MYTH_ART_PATH = Path(__file__).parent.parent / "data" / "myth_art.json"
try:
    _MYTH_ART: dict = json.loads(_MYTH_ART_PATH.read_text())
except Exception:
    _MYTH_ART = {}


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


def _search_titles(query: str) -> list[str]:
    """Search Commons files by arbitrary query string."""
    results = _api({
        "action": "query", "list": "search",
        "srsearch": query, "srnamespace": "6", "srlimit": "40",
    }).get("query", {}).get("search", [])
    return _image_titles([r.get("title", "") for r in results])


def _image_from_titles(titles: list[str]) -> dict | None:
    """Batch-query candidates, return the first that carries a real image url."""
    sample = random.sample(titles, min(15, len(titles)))
    pages = _api({
        "action": "query", "prop": "imageinfo", "titles": "|".join(sample),
        "iiprop": "url|extmetadata",
    }).get("query", {}).get("pages", {})
    for page in list(pages.values()):
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


def _fetch_art(
    category: str,
    name: str | None = None,
    alt_categories: list[str] | None = None,
    search_terms: list[str] | None = None,
) -> dict | None:
    """
    Multi-strategy Wikimedia image lookup. Stops at first hit:
    1. Primary category
    2. Alt categories (in order)
    3. Explicit search terms (in order)
    4. Generic name-based search
    5. Historical atlas corpus (Uranometria, Flamsteed, Hevelius)
    """
    try:
        titles = _category_titles(category)
        art = _image_from_titles(titles) if titles else None
        if art:
            return art

        for alt_cat in (alt_categories or []):
            titles = _category_titles(alt_cat)
            art = _image_from_titles(titles) if titles else None
            if art:
                return art

        for term in (search_terms or []):
            titles = _search_titles(term)
            art = _image_from_titles(titles) if titles else None
            if art:
                return art

        if name:
            titles = _search_titles(f"{name} constellation mythology art")
            art = _image_from_titles(titles) if titles else None
            if art:
                return art

        if name:
            for atlas in ("Uranometria", "Flamsteed", "Hevelius"):
                titles = _search_titles(f"{name} {atlas}")
                art = _image_from_titles(titles) if titles else None
                if art:
                    return art

        return None
    except Exception:
        logger.exception("Wikimedia art fetch failed for %s", category)
        return None


def _strip(html: str) -> str:
    """Crude tag strip — Artist value is often wrapped in <a>…</a>."""
    return re.sub(r"<[^>]+>", "", html).strip()


def get_constellation_art(name: str) -> dict | None:
    cached = _CACHE.get(name)
    if cached and (time.time() - cached[0]) < CACHE_TTL_SECONDS:
        return cached[1]
    entry = _MYTH_ART.get(name)
    if not entry:
        return None
    art = _fetch_art(entry["category"], name, entry.get("alt_categories", []), entry.get("search_terms", []))
    if art is not None:
        _CACHE[name] = (time.time(), art)
    return art
