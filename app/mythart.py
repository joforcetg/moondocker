import json
import logging
import random
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


def _fetch_art(category: str) -> dict | None:
    """One random file from `category`, with imageinfo. None on any problem."""
    try:
        members = _api({
            "action": "query", "list": "categorymembers",
            "cmtitle": category, "cmtype": "file", "cmlimit": "100",
        }).get("query", {}).get("categorymembers", [])
        if not members:
            return None
        title = random.choice(members)["title"]
        pages = _api({
            "action": "query", "prop": "imageinfo", "titles": title,
            "iiprop": "url|extmetadata",
        }).get("query", {}).get("pages", {})
        page = next(iter(pages.values()), {})
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("url")
        if not url:
            return None
        ext = info.get("extmetadata", {})
        return {
            "url": url,
            "title": title.removeprefix("File:"),
            "author": _strip(ext.get("Artist", {}).get("value", "")),
            "license": ext.get("LicenseShortName", {}).get("value", ""),
            "credit_url": info.get("descriptionurl", ""),
        }
    except Exception:
        logger.exception("Wikimedia art fetch failed for %s", category)
        return None


def _strip(html: str) -> str:
    """Crude tag strip — Artist value is often wrapped in <a>…</a>."""
    import re
    return re.sub(r"<[^>]+>", "", html).strip()


def get_constellation_art(name: str, category: str) -> dict | None:
    cached = _CACHE.get(name)
    if cached and (time.time() - cached[0]) < CACHE_TTL_SECONDS:
        return cached[1]
    art = _fetch_art(category)
    if art is not None:
        _CACHE[name] = (time.time(), art)
    return art
