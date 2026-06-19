# Narrative & Image Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Richer myth/folklore content, multi-strategy Wikimedia image lookup, cold skymap palette, and wordmark rename.

**Architecture:** Pure data changes for content files (JSON); targeted code refactor for `mythart.py`; color-only change for `skymap.py`; trivial text edits for `index.html` and `app.js`. No new dependencies, no API changes.

**Tech Stack:** Python 3.13, FastAPI, vanilla JS, JSON data files.

## Global Constraints

- All Python commands: `.venv/bin/python` (system Python lacks deps)
- Test runner: `.venv/bin/python -m pytest -v` (requires `dangerouslyDisableSandbox: true`)
- 57 tests must pass after every task
- `app.main.*` patch targets must not change (do not switch to `astronomy.*` style)
- `get_constellation_art(name: str, category: str) -> dict | None` signature unchanged
- Cast entries in `myths.json` must be exact names from `constellations.json`: Andromeda, Aquarius, Aquila, Auriga, Boötes, Canis Major, Cassiopeia, Cygnus, Gemini, Hercules, Leo, Lyra, Orion, Perseus, Sagittarius, Scorpius, Taurus, Ursa Major, Ursa Minor, Virgo

---

### Task 1: Rename wordmark

**Files:**
- Modify: `app/static/index.html`

**Interfaces:**
- Produces: nothing consumed by other tasks

- [ ] **Step 1: Edit `app/static/index.html`**

Change both occurrences of `moondocker` to `Moonseek`:

```html
<title>Moonseek</title>
```

```html
<span class="wordmark">Moonseek</span>
```

- [ ] **Step 2: Run tests**

```bash
.venv/bin/python -m pytest -v
```

Expected: 57 passed (no test asserts the wordmark text).

- [ ] **Step 3: Commit**

```bash
git add app/static/index.html
git commit -m "feat: rename wordmark to Moonseek"
```

---

### Task 2: Skymap cold palette

**Files:**
- Modify: `app/skymap.py`

**Interfaces:**
- Produces: nothing consumed by other tasks

- [ ] **Step 1: Edit `app/skymap.py` — update five color values**

Current → new:

| Line | Old value | New value |
|---|---|---|
| constellation lines stroke | `"#6b6256"` | `"#4a4a52"` |
| figure star fill | `"#ece7da"` | `"#cacace"` |
| background star fill | `"#cfc8b8"` | `"#9a9aa8"` |
| background star fill-opacity | `"0.85"` | `"0.6"` |
| cardinal text fill | `"#8a8276"` | `"#7e7e85"` |

Full updated `generate_skymap` function (only changed lines shown with `# changed`):

```python
def generate_skymap(
    stars: list[dict],
    const_lines: list[dict],
) -> str:
    hip_xy: dict[int, tuple[float, float]] = {
        s["hip_id"]: az_alt_to_xy(s["az"], s["alt"]) for s in stars
    }

    fig_members: dict[int, set[str]] = {}
    lines_svg = []
    for seg in const_lines:
        a, b = seg["hip_a"], seg["hip_b"]
        name = seg["constellation"]
        if a in hip_xy and b in hip_xy:
            x1, y1 = hip_xy[a]
            x2, y2 = hip_xy[b]
            lines_svg.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'data-constellation="{name}" '
                f'stroke="#4a4a52" stroke-width="0.8" stroke-opacity="0.7"/>'  # changed
            )
            fig_members.setdefault(a, set()).add(name)
            fig_members.setdefault(b, set()).add(name)

    stars_svg = []
    for s in stars:
        x, y = hip_xy[s["hip_id"]]
        r = star_radius(s["magnitude"])
        members = fig_members.get(s["hip_id"])
        if members:
            tag = " ".join(sorted(members))
            stars_svg.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" '
                f'data-constellation="{tag}" class="figstar" '
                f'fill="#cacace" fill-opacity="0.95"/>'  # changed
            )
        else:
            stars_svg.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" '
                f'fill="#9a9aa8" fill-opacity="0.6"/>'  # changed
            )

    cardinals = [("N", 0), ("E", 90), ("S", 180), ("W", 270)]
    cardinal_svg = []
    for label, az in cardinals:
        x, y = az_alt_to_xy(az, 0.0)
        scale = (R + 12) / R
        lx = CX + (x - CX) * scale
        ly = CY + (y - CY) * scale
        cardinal_svg.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" fill="#7e7e85" font-size="10" '  # changed
            f'text-anchor="middle" dominant-baseline="middle" '
            f'font-family="serif">{label}</text>'
        )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Night sky map: stars and constellation figures above the horizon" '
        f'viewBox="0 0 {VIEWBOX_SIZE} {VIEWBOX_SIZE}" '
        f'width="{VIEWBOX_SIZE}" height="{VIEWBOX_SIZE}" style="background:#08080a">',
        '<title>Night sky map</title>',
        f'<circle cx="{CX:.1f}" cy="{CY:.1f}" r="{R:.1f}" fill="#08080a" '
        f'stroke="#2a2a2e" stroke-width="1"/>',
        *lines_svg,
        *stars_svg,
        *cardinal_svg,
        "</svg>",
    ]
    return "\n".join(parts)
```

- [ ] **Step 2: Run tests**

```bash
.venv/bin/python -m pytest -v
```

Expected: 57 passed.

- [ ] **Step 3: Commit**

```bash
git add app/skymap.py
git commit -m "fix(skymap): cold steel palette — drop warm sepia tones"
```

---

### Task 3: app.js constellation marker polish

**Files:**
- Modify: `app/static/app.js`

**Interfaces:**
- Produces: nothing consumed by other tasks

- [ ] **Step 1: Edit `app/static/app.js` — change two marker symbols**

In `renderConstellations`, find:

```js
'<span class="const-marker">' + (c.above_horizon ? '▲' : '▽') + '</span>' +
```

Replace with:

```js
'<span class="const-marker">' + (c.above_horizon ? '·' : '∘') + '</span>' +
```

- [ ] **Step 2: Run tests**

```bash
.venv/bin/python -m pytest -v
```

Expected: 57 passed (no test asserts marker symbols).

- [ ] **Step 3: Commit**

```bash
git add app/static/app.js
git commit -m "fix(ui): quieter constellation markers · ∘"
```

---

### Task 4: myth_art.json — alt categories and search terms

**Files:**
- Modify: `data/myth_art.json`

**Interfaces:**
- Produces: `alt_categories` and `search_terms` fields consumed by Task 5 (`mythart.py`)

- [ ] **Step 1: Replace `data/myth_art.json` with expanded schema**

Write the full file:

```json
{
  "Orion": {
    "category": "Category:Orion in art",
    "alt_categories": [
      "Category:Orion (mythology) in art",
      "Category:Uranometria"
    ],
    "search_terms": [
      "Orion constellation Bayer Uranometria",
      "Orion hunter mythology engraving"
    ]
  },
  "Ursa Major": {
    "category": "Category:Ursa Major in art",
    "alt_categories": [
      "Category:Callisto (mythology)",
      "Category:Urania's Mirror"
    ],
    "search_terms": [
      "Ursa Major constellation Flamsteed",
      "Great Bear constellation engraving"
    ]
  },
  "Cassiopeia": {
    "category": "Category:Cassiopeia (mythology)",
    "alt_categories": [
      "Category:Cassiopeia (constellation) in art",
      "Category:Firmamentum Sobiescianum"
    ],
    "search_terms": [
      "Cassiopeia constellation Hevelius",
      "Cassiopeia queen mythology engraving"
    ]
  },
  "Leo": {
    "category": "Category:Leo (constellation) in art",
    "alt_categories": [
      "Category:Nemean lion",
      "Category:Uranometria"
    ],
    "search_terms": [
      "Leo constellation Bayer Uranometria",
      "Nemean lion Hercules mythology art"
    ]
  },
  "Scorpius": {
    "category": "Category:Scorpius (constellation) in art",
    "alt_categories": [
      "Category:Scorpius (constellation)",
      "Category:Uranometria"
    ],
    "search_terms": [
      "Scorpius constellation Bayer engraving",
      "scorpion mythology constellation art"
    ]
  },
  "Cygnus": {
    "category": "Category:Zeus metamorphoses",
    "alt_categories": [
      "Category:Cygnus (constellation) in art",
      "Category:Leda and the swan"
    ],
    "search_terms": [
      "Cygnus constellation Bayer Uranometria",
      "swan Zeus mythology art"
    ]
  },
  "Lyra": {
    "category": "Category:Orpheus in art",
    "alt_categories": [
      "Category:Lyra (constellation) in art",
      "Category:Eurydice (mythology)"
    ],
    "search_terms": [
      "Lyra constellation Flamsteed",
      "Orpheus lyre mythology engraving"
    ]
  },
  "Aquila": {
    "category": "Category:Zeus metamorphoses",
    "alt_categories": [
      "Category:Aquila (constellation) in art",
      "Category:Ganymede (mythology)"
    ],
    "search_terms": [
      "Aquila constellation Hevelius engraving",
      "eagle Zeus Ganymede mythology art"
    ]
  },
  "Gemini": {
    "category": "Category:Dioscuri in art",
    "alt_categories": [
      "Category:Castor and Pollux",
      "Category:Urania's Mirror"
    ],
    "search_terms": [
      "Gemini constellation engraving Flamsteed",
      "Dioscuri twins mythology art"
    ]
  },
  "Taurus": {
    "category": "Category:Europa and the bull",
    "alt_categories": [
      "Category:Taurus (constellation) in art",
      "Category:Uranometria"
    ],
    "search_terms": [
      "Taurus constellation Bayer Uranometria",
      "Zeus Europa bull mythology engraving"
    ]
  },
  "Virgo": {
    "category": "Category:Demeter in art",
    "alt_categories": [
      "Category:Virgo (constellation) in art",
      "Category:Persephone in art"
    ],
    "search_terms": [
      "Virgo constellation Flamsteed",
      "Demeter Persephone mythology harvest art"
    ]
  },
  "Boötes": {
    "category": "Category:Boötes (constellation)",
    "alt_categories": [
      "Category:Boötes (constellation) in art",
      "Category:Arcas (mythology)"
    ],
    "search_terms": [
      "Bootes constellation Hevelius engraving",
      "Bootes herdsman constellation Firmamentum"
    ]
  },
  "Perseus": {
    "category": "Category:Perseus in art",
    "alt_categories": [
      "Category:Perseus (mythology) in art",
      "Category:Andromeda and Perseus"
    ],
    "search_terms": [
      "Perseus constellation Bayer Uranometria",
      "Perseus Medusa mythology engraving"
    ]
  },
  "Auriga": {
    "category": "Category:Auriga (constellation)",
    "alt_categories": [
      "Category:Auriga (constellation) in art",
      "Category:Firmamentum Sobiescianum"
    ],
    "search_terms": [
      "Auriga charioteer constellation Hevelius",
      "Auriga constellation Uranometria engraving"
    ]
  },
  "Canis Major": {
    "category": "Category:Canis Major (constellation)",
    "alt_categories": [
      "Category:Canis Major (constellation) in art",
      "Category:Sirius (star)"
    ],
    "search_terms": [
      "Canis Major constellation Bayer Uranometria",
      "Sirius dog star mythology engraving"
    ]
  },
  "Aquarius": {
    "category": "Category:Aquarius (constellation) in art",
    "alt_categories": [
      "Category:Aquarius (constellation)",
      "Category:Ganymede (mythology)"
    ],
    "search_terms": [
      "Aquarius constellation Flamsteed engraving",
      "water bearer mythology art constellation"
    ]
  },
  "Sagittarius": {
    "category": "Category:Sagittarius (constellation) in art",
    "alt_categories": [
      "Category:Sagittarius (constellation)",
      "Category:Chiron (mythology)"
    ],
    "search_terms": [
      "Sagittarius constellation Bayer Uranometria",
      "centaur archer mythology engraving"
    ]
  },
  "Hercules": {
    "category": "Category:Hercules in art",
    "alt_categories": [
      "Category:Hercules (mythology) in art",
      "Category:Twelve Labours of Hercules"
    ],
    "search_terms": [
      "Hercules constellation Hevelius Firmamentum",
      "Hercules labors mythology art engraving"
    ]
  },
  "Ursa Minor": {
    "category": "Category:Ursa Minor in art",
    "alt_categories": [
      "Category:Ursa Minor (constellation) in art",
      "Category:Urania's Mirror"
    ],
    "search_terms": [
      "Ursa Minor constellation Flamsteed",
      "Little Bear constellation engraving"
    ]
  },
  "Andromeda": {
    "category": "Category:Andromeda (mythology)",
    "alt_categories": [
      "Category:Andromeda (constellation) in art",
      "Category:Perseus rescuing Andromeda"
    ],
    "search_terms": [
      "Andromeda constellation Bayer Uranometria",
      "Andromeda chained mythology art engraving"
    ]
  }
}
```

- [ ] **Step 2: Run tests**

```bash
.venv/bin/python -m pytest -v
```

Expected: 57 passed (no test reads `myth_art.json` directly).

- [ ] **Step 3: Commit**

```bash
git add data/myth_art.json
git commit -m "feat(data): add alt_categories and search_terms to myth_art.json"
```

---

### Task 5: `mythart.py` multi-strategy lookup

**Files:**
- Modify: `app/mythart.py`
- Modify: `tests/test_mythart.py`

**Interfaces:**
- Consumes: `data/myth_art.json` new `alt_categories` / `search_terms` fields (Task 4)
- Produces: `get_constellation_art(name, category)` unchanged signature

- [ ] **Step 1: Write failing tests — append to `tests/test_mythart.py`**

Add these six tests at the end of the file:

```python
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
```

- [ ] **Step 2: Run failing tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_mythart.py -v -k "falls_back or strategies or reads_alt"
```

Expected: all new tests FAIL (functions not yet updated).

- [ ] **Step 3: Rewrite `app/mythart.py`**

Replace the entire file with:

```python
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


def get_constellation_art(name: str, category: str) -> dict | None:
    cached = _CACHE.get(name)
    if cached and (time.time() - cached[0]) < CACHE_TTL_SECONDS:
        return cached[1]
    entry = _MYTH_ART.get(name, {})
    alt_categories = entry.get("alt_categories", [])
    search_terms = entry.get("search_terms", [])
    art = _fetch_art(category, name, alt_categories, search_terms)
    if art is not None:
        _CACHE[name] = (time.time(), art)
    return art
```

- [ ] **Step 4: Run all tests**

```bash
.venv/bin/python -m pytest -v
```

Expected: 63 passed (57 existing + 6 new), 1 warning.

- [ ] **Step 5: Commit**

```bash
git add app/mythart.py tests/test_mythart.py
git commit -m "feat(mythart): 5-strategy Wikimedia lookup with atlas fallback"
```

---

### Task 6: `myths.json` — expand texts and add non-Greek myths

**Files:**
- Modify: `data/myths.json`

**Interfaces:**
- Produces: nothing consumed by other tasks (tests mock `pick_constellation_myth`)

- [ ] **Step 1: Replace `data/myths.json` with expanded content**

Write the full file. All 31 existing entries are expanded to 4–6 sentences. 15 new non-Greek entries are appended. Cast names must exactly match the Global Constraints list.

```json
[
  {
    "id": "orion-scorpius",
    "title": "The Hunter and the Scorpion",
    "text": "Orion was the greatest hunter the world had known — son of Poseidon, who could walk upon the waves — and he boasted he would hunt every beast upon the earth until nothing living remained. Gaia, mother of all creatures, heard the boast and sent a scorpion from the cracks in the ground, armoured with a shell no blade could pierce. It stung him at the heel, the only place his divine blood had not fully hardened, and Orion fell. Zeus set them both in the sky, but could not reconcile them even there: when Scorpius rises in the east, Orion sinks below the western horizon, still retreating. Sailors called this opposition the most reliable of seasonal clocks — the hunter's exit marked the coming of summer heat.",
    "cast": ["Orion", "Scorpius"]
  },
  {
    "id": "perseus-andromeda",
    "title": "The Chained Princess",
    "text": "Cassiopeia, queen of Ethiopia, declared her own beauty and her daughter Andromeda's surpassed the Nereids, Poseidon's sea-nymphs. The god sent the sea-monster Cetus to devour the coast, and the oracle ruled that only Andromeda's sacrifice would end the destruction. She was chained naked to a sea-cliff to await the beast when Perseus arrived overhead, returning from Libya with Medusa's severed head still dripping in its sack. He struck a bargain with her parents — her hand in marriage for her life — then held the head above the waves as Cetus surfaced, turning the creature to stone before it could reach her. All five figures in the myth — Perseus, Andromeda, Cassiopeia, Cepheus, and the sea-monster — were placed in the sky to preserve the story.",
    "cast": ["Perseus", "Andromeda", "Cassiopeia"]
  },
  {
    "id": "callisto-bears",
    "title": "The Bear Mother",
    "text": "Callisto was a huntress in Artemis's company who had sworn to remain a virgin, but Zeus came to her in disguise and fathered a child. When the pregnancy showed, Artemis expelled her; Hera, jealous even of a forced union, transformed her into a bear. Callisto wandered the forest for years — a bear with a woman's mind — until her grown son Arcas levelled a spear at the shaggy creature without knowing it was his mother. Zeus intervened at the last moment, sweeping them both upward to become the Great Bear and the Little Bear, placed at the pole to circle together forever, never allowed to sink below the horizon and sleep.",
    "cast": ["Ursa Major", "Ursa Minor", "Boötes"]
  },
  {
    "id": "orpheus-lyre",
    "title": "The Lyre of Orpheus",
    "text": "Orpheus was given a lyre by Apollo and taught by the Muses; when he played, rivers paused in their courses, rocks moved to hear him, and wild beasts lay down their savagery. When his wife Eurydice died of a serpent's bite, he descended to the underworld and played before Persephone and Hades until they wept — an unprecedented thing — and Eurydice was returned to him on the condition he not look back until they had reached the surface. He looked. Grief-maddened, he wandered the hills of Thrace refusing all other love, until the Maenads tore him apart. His head floated down the Hebrus river still singing; the gods placed his lyre in the sky so its music would never be silenced.",
    "cast": ["Lyra"]
  },
  {
    "id": "cygnus-phaethon",
    "title": "Swan of Grief",
    "text": "Phaethon was the son of Helios and had always doubted his divine parentage; when Helios granted him any wish, he asked to drive the sun-chariot for one day. The horses, sensing an unfamiliar hand, bolted; the chariot scorched the deserts of Libya, then plunged toward the north and froze the Scythian plains. Zeus struck Phaethon from the car with a thunderbolt before the world could be consumed, and the boy fell blazing into the river Eridanus. His dearest companion Cycnus wandered the riverbank for the rest of his days weeping until the gods took pity, transformed him into a swan, and lifted him into the sky.",
    "cast": ["Cygnus"]
  },
  {
    "id": "zeus-eagle",
    "title": "The Eagle of Zeus",
    "text": "Aquila was the messenger and weapons-carrier of Zeus, the eagle that bore the divine thunderbolts through the sky between storms. Zeus dispatched the bird to abduct the beautiful Trojan shepherd Ganymede from the slopes of Mount Ida, lifting the boy in its talons and bearing him to Olympus to serve as cupbearer to the gods. There Ganymede poured nectar at the feasts of the immortals, replacing Hebe, daughter of Hera — an insult the goddess never forgave. The eagle was placed in the heavens in honour of its service, and Ganymede's figure follows nearby, ever-pouring, a figure of grace at the edge of the celestial court.",
    "cast": ["Aquila", "Aquarius"]
  },
  {
    "id": "castor-pollux",
    "title": "The Twin Stars",
    "text": "Castor and Pollux were born from the same mother, Leda of Sparta, but from different fathers — Castor from the mortal king Tyndareus, Pollux from Zeus who visited Leda in the shape of a swan. They were inseparable in life: soldiers, horsemen, and patron saints of shipwrecked sailors, who looked for them in the electrical fire that plays at a ship's masthead in a storm. When Castor was killed in a cattle raid, Pollux could not bear to take sole possession of the immortality his divine blood had given him. He begged Zeus to let him share it with his dead brother; the god placed them together in the sky, their stars shining side by side through all the winter nights.",
    "cast": ["Gemini"]
  },
  {
    "id": "zeus-europa",
    "title": "The Bull Across the Sea",
    "text": "Zeus took the form of a white bull, perfect and gentle, to approach the Phoenician princess Europa as she gathered flowers by the shore. She placed garlands on its horns, climbed its broad back on a whim, and the bull walked into the sea and began to swim — crossing the entire width of the Mediterranean without pausing, carrying Europa to the island of Crete. There Zeus revealed his true form; from their union came Minos, Rhadamanthus, and Sarpedon, three kings who shaped the ancient world. The bull's starry form was set in the sky, half-submerged as if still rising from the waves.",
    "cast": ["Taurus"]
  },
  {
    "id": "demeter-virgo",
    "title": "The Harvest Goddess",
    "text": "When Persephone was taken to the underworld, her mother Demeter laid aside her divine duties and wandered the world as a mortal woman, too deep in grief to govern the harvest. The crops withered, cattle died, and humankind faced starvation until Zeus brokered the bargain that returned Persephone for half of every year. The figure of Virgo holding a sheaf of grain is interpreted by most as Demeter herself; others say it is Persephone, returning each spring. She holds the bright star Spica in her left hand — the ripened wheat-ear — a reminder that the harvest's plenty depends on a mother's conditional consent.",
    "cast": ["Virgo"]
  },
  {
    "id": "nemean-lion",
    "title": "The Unconquerable Beast",
    "text": "The Nemean Lion was no natural creature but an offspring of the divine monsters Typhon and Echidna, placed by Hera in the hills outside Nemea to terrorize the countryside. Its hide turned away every weapon — bronze, iron, and obsidian all failed. Hercules arrived on his first labor and tried arrows and sword before he understood; he wrestled the beast with bare hands and strangled it. He then used the lion's own claws — the only things that could cut its hide — to skin it, draping the pelt across his shoulders for the rest of his mortal life. Hera placed the lion's image in the sky as a memorial to the one thing her chosen monster had failed to destroy.",
    "cast": ["Leo", "Hercules"]
  },
  {
    "id": "erichthonius-chariot",
    "title": "The Lame King and His Chariot",
    "text": "Erichthonius was born from the earth itself — lame from his first breath — and refused to be confined. He studied the movement of horses and invented the four-horse chariot, building a vehicle that gave his crippled body the speed the gods had denied him. Athena looked on his ingenuity with favour; when he became king of Athens he introduced the Panathenaic games. His image among the stars is that of a charioteer, whip in one hand, sometimes shown carrying the she-goat Amalthea to explain the scattered nearby stars.",
    "cast": ["Auriga"]
  },
  {
    "id": "orion-canis",
    "title": "The Faithful Hounds",
    "text": "Orion's great hound bore the name Sirius, brightest of all stars, and ran at his master's heel through every hunt. Sirius was said to rise with the sun in summer, adding its own heat to the day and causing the sweltering weeks the Greeks called the Dog Days — the same weeks when rivers shrank and fevers spread. When Orion was placed in the sky, his faithful companion followed: Canis Major at his heel, the brilliance of Sirius blazing so fiercely that ancient astronomers credited it with the drying of rivers in August. The two figures stride together across the winter sky.",
    "cast": ["Orion", "Canis Major"]
  },
  {
    "id": "sagittarius-chiron",
    "title": "The Wise Archer",
    "text": "Chiron was unlike other centaurs: son of the Titan Cronus and gentle where his kin were violent, a master of medicine, music, archery, and prophecy who tutored the greatest heroes — Achilles, Jason, and Asclepius among them. He was accidentally struck by one of Hercules' arrows tipped with the lethal blood of the Lernaean Hydra, and found himself dying in agony, unable to die permanently because of his immortality. He surrendered his divinity to Prometheus in exchange for release from the pain. Zeus placed his figure among the stars in recognition of his selfless bargain — the healer who chose death rather than endless suffering.",
    "cast": ["Sagittarius"]
  },
  {
    "id": "hercules-labors",
    "title": "The Labors Written in Stars",
    "text": "Hercules committed his gravest act in a moment of madness sent by Hera: he killed his wife Megara and their children. When the fit passed and he understood what he had done, he went to the oracle at Delphi to learn how to expiate the crime. The oracle sent him to serve King Eurystheus for twelve years, performing whatever labors the king devised — he slew the Nemean lion and the nine-headed Hydra, captured the Cretan bull and the mares of Diomedes, descended to the underworld and led Cerberus out on a chain. When he died and was burned on Mount Oeta, his mortal portion was consumed in the flames and his divine nature rose to take its place among the stars.",
    "cast": ["Hercules"]
  },
  {
    "id": "bootes-ploughman",
    "title": "The Ploughman Who Would Not Stop",
    "text": "Boötes is called the Herdsman or the Ploughman, and different traditions assign him different identities. Some say he is Arcas, the son of Callisto, who invented the plough and the oxen-yoke and was placed in the sky for giving agriculture to humankind. Others name him Icarius, the first man to whom Dionysus taught wine-making; when Icarius shared wine with shepherds who did not know its power, they killed him thinking he had poisoned them. His dog Maera led his daughter Erigone to the body; all three were placed in the sky together. He follows the Great Bear across the northern sky, his bright star Arcturus the fourth-brightest in all the heavens.",
    "cast": ["Boötes", "Ursa Major"]
  },
  {
    "id": "perseus-gorgon",
    "title": "The Head That Turned Worlds to Stone",
    "text": "Perseus was sent by King Polydectes to bring back Medusa's head — a mission intended to be a death sentence. He received gifts from the gods: a mirrored shield from Athena, winged sandals from Hermes, and a helmet of invisibility from Hades. He approached the sleeping Medusa looking only at her reflection in the shield, cut off her head, and sealed it in a sack before he could meet her gaze. As he flew back across Libya, drops of blood fell from the sack and became the desert's serpents; from Medusa's neck sprang the winged horse Pegasus. He used the head to save Andromeda and to turn the Titan Atlas to stone before giving it to Athena, who placed it on her shield.",
    "cast": ["Perseus"]
  },
  {
    "id": "cassiopeia-pride",
    "title": "The Queen in Her Chair",
    "text": "Cassiopeia was queen of the Ethiopian coast and could not resist the comparison: she claimed her own beauty and her daughter Andromeda's surpassed the sea-nymphs of Poseidon's court. The Nereids complained to the sea-god, who sent the monster Cetus to devastate the coastline and demand Andromeda's sacrifice. Perseus intervened and saved her, but Cassiopeia's punishment was not yet finished. She was placed in the sky circling the pole, seated on her throne, and for half of every night she hangs upside down — a humiliating reminder that no mortal beauty can be called greater than the divine.",
    "cast": ["Cassiopeia", "Andromeda"]
  },
  {
    "id": "scorpius-artemis",
    "title": "Artemis and the Scorpion",
    "text": "Orion's pride extended not only to his hunting but to his friendship with Artemis, goddess of the hunt, and some say she loved him. When he declared he would rid the earth of every beast, Gaia interceded; some accounts say Artemis herself, manipulated by her jealous brother Apollo, fired the arrow that ended Orion's life — Apollo pointing out a dark shape in the water that was in fact the hunter's head. However it happened, both Orion and the scorpion Gaia sent were placed in opposing parts of the sky. When one rises, the other must set; they never share the same horizon.",
    "cast": ["Scorpius", "Orion"]
  },
  {
    "id": "cygnus-zeus",
    "title": "Zeus and Leda",
    "text": "Zeus came to Leda of Sparta in the form of a swan, and from that encounter she bore four children — some from eggs, in the oldest tellings. Castor and Pollux came from one egg; Helen and Clytemnestra from another. Helen's abduction from Sparta by the Trojan prince Paris set in motion the greatest war of the ancient world, a cascade of destruction that began with a swan on a riverbank. The swan's shape was honoured with a place among the stars — some say in thanks, others as a reminder that the gods reach into mortal life in shapes the unwary cannot recognise.",
    "cast": ["Cygnus", "Gemini"]
  },
  {
    "id": "aquarius-deucalion",
    "title": "The Water-Bearer and the Flood",
    "text": "The human race had grown wicked and Zeus resolved to wash them away with a great flood. He warned only Prometheus, who passed the warning to his son Deucalion; Deucalion and his wife Pyrrha built a great chest and survived on the waters for nine days and nights until the peaks of Parnassus emerged. To repopulate the earth, they were told to throw the bones of their mother behind them; taking this to mean the stones of the earth, they did so, and where each stone landed a new human being arose. Some say the figure of Aquarius pouring his endless jar is Deucalion himself, still pouring out the waters of the flood long after it has passed.",
    "cast": ["Aquarius"]
  },
  {
    "id": "taurus-pleiades",
    "title": "The Bull and the Seven Sisters",
    "text": "The Pleiades were seven sisters, daughters of Atlas the Titan, who caught the eye of the hunter Orion. To protect them from his pursuit, Zeus transformed them first into doves and then into stars, placing them in the shoulder of the Bull so the constellation itself would deter Orion from approaching. He did not stop: the Pleiades rise in the east ahead of Orion each spring, and he follows until winter comes. Sailors of the Mediterranean dated their sailing season by the Pleiades' rising and feared the storms of their setting; the loss of one sister — Electra, or Merope, depending on the teller — explains why only six stars are clearly visible.",
    "cast": ["Taurus", "Orion"]
  },
  {
    "id": "ursa-minor-pole",
    "title": "The Unchanging Star",
    "text": "Ursa Minor circles so close to the celestial pole that her brightest star scarcely moves across the night sky. Phoenician and later Greek sailors steered all courses by this star, which they called Cynosura — the dog's tail — from the constellation's appearance. The myth behind the figure is usually the same as Ursa Major: Callisto and her son Arcas, placed at the pole to circle together forever. The bear cannot sleep, cannot sink below the horizon; the gods who set her there gave her no rest.",
    "cast": ["Ursa Minor"]
  },
  {
    "id": "leo-nemean",
    "title": "Child of Echidna",
    "text": "The Nemean Lion was placed by Hera in the hills of Nemea to be a test no mortal could survive, and for a time none did. The beast was proof against weapons — its golden hide turned aside every blade — and it fed freely on the livestock and people of the region. Hercules arrived on his first labor, tried arrows first, watching them bounce aside, then his sword, then his club, before he drove the lion into a cave and wrestled it with bare hands. He skinned it with its own claws and wore the hide for the rest of his mortal life. Hera placed the lion among the stars as proof that even her greatest instrument had not been enough.",
    "cast": ["Leo"]
  },
  {
    "id": "lyra-sirens",
    "title": "Music Against the Darkness",
    "text": "When Jason and the Argonauts sailed past the island of the Sirens — women whose song drew sailors irresistibly to their deaths on the rocks — it was Orpheus who saved them. He took up his lyre and played so loudly, with a melody so compelling, that the crew of the Argo heard only his music and rowed past in safety. Only one man, Butes, leapt into the sea to swim toward the Sirens' voices; Aphrodite plucked him from the waves before he reached them. The lyre that held death at bay for the Argonauts was eventually placed in the sky after Orpheus's death, positioned near the eagle so the music of the lyre could harmonise forever with the eagle's cry.",
    "cast": ["Lyra"]
  },
  {
    "id": "virgo-persephone",
    "title": "The Maiden Returned",
    "text": "Persephone was gathering narcissus flowers in a meadow when the earth split open and Hades rode up in his chariot to take her below. Demeter searched for nine days without stopping before Helios told her what he had seen. She withdrew her gifts from the earth — crops failed, animals refused to breed, and the dead began to outnumber the living. Zeus brokered a compromise: Persephone had eaten six pomegranate seeds in the underworld, so she would spend six months below and six months above. Virgo rises in spring with Persephone's return and fades from the autumn sky as she descends.",
    "cast": ["Virgo"]
  },
  {
    "id": "auriga-myrtilus",
    "title": "The Cursed Charioteer",
    "text": "Myrtilus was the charioteer of King Oenomaus, who had declared that only a man who could beat him in a chariot race could marry his daughter Hippodamia — and then had the suitors killed when they lost. Pelops bribed Myrtilus to replace the bronze linchpins of his master's chariot wheels with wax; the wheels came off at speed and Oenomaus was dragged to his death. Pelops married Hippodamia as promised but refused to pay Myrtilus the reward they had agreed. When Pelops threw him from a cliff into the sea, Myrtilus cursed the house of Pelops as he drowned — a curse that ran down through the generations into the story of Agamemnon and Orestes. The charioteer's figure was placed in the sky as witness to the original act of treachery.",
    "cast": ["Auriga"]
  },
  {
    "id": "aquila-prometheus",
    "title": "The Eagle of Punishment",
    "text": "Prometheus stole fire from the forge of Hephaestus on Olympus and carried it down to humanity in the hollow of a fennel stalk. Zeus's punishment was exemplary and eternal: Prometheus was chained to a rock on the Caucasus mountains, and each dawn the eagle flew down to tear out his liver, which grew back each night so the punishment could never end. The rock was chosen because it was too high for any mortal to climb. When Hercules performed his labors and passed through the Caucasus, he killed the eagle with an arrow from below and broke the chains. Zeus placed the eagle in the sky to commemorate the long service — others say as a memorial to his own defeated revenge.",
    "cast": ["Aquila", "Hercules"]
  },
  {
    "id": "canis-major-laelaps",
    "title": "The Hound That Always Caught Its Quarry",
    "text": "Laelaps was a hunting dog given by Zeus to Europa, passed through several hands until it came to Procris, wife of Cephalus, bearing the divine property of never missing its quarry. When it was set to hunt the Teumessian Fox — a monstrous beast sent by Dionysus that was destined never to be caught — Zeus looked down at the paradox of an unerring dog hunting an uncatchable fox and saw that it had no resolution. He turned both animals to stone and placed them in the heavens. Canis Major carries Sirius, the brightest star in the night sky, at its snout — the immortal hound still pointing, the hunt permanently interrupted.",
    "cast": ["Canis Major"]
  },
  {
    "id": "sagittarius-dionysus",
    "title": "The Satyr Who Taught the Vine",
    "text": "Crotus was the son of Pan and grew up on the slopes of Mount Helicon among the Muses, who taught him their arts. He was said to be the first archer, inventing the technique of shooting with a rhythmic beat to steady the hand. He accompanied Dionysus across Asia, learning the art of the vine and protecting the god's retinue with his bow. When he died, the nine Muses petitioned Zeus together — an unusual occurrence — to place their companion in the sky. Zeus agreed and gave him a position straddling the great band of the Milky Way, his arrow pointing toward Antares in the heart of the Scorpion.",
    "cast": ["Sagittarius"]
  },
  {
    "id": "perseus-atlas",
    "title": "The Gorgon and the Titan",
    "text": "After killing Medusa and rescuing Andromeda, Perseus flew west across the Libyan desert and reached the garden of the Hesperides at the world's edge, where Atlas stood holding the vault of heaven on his shoulders. Perseus asked for hospitality; Atlas refused, having been warned by a prophecy that a son of Zeus would come and steal the golden apples of the Hesperides. Perseus drew the Gorgon's head from its bag and held it up; Atlas, weighing more than any mountain, turned to stone where he stood, and his petrified body became the Atlas mountain range that still bears the weight of the sky on its ridges.",
    "cast": ["Perseus"]
  },
  {
    "id": "bootes-arcas",
    "title": "The Son Who Did Not Know",
    "text": "Arcas was raised by his grandfather after his mother Callisto was transformed into a bear, and he grew up to be a skilled hunter with no knowledge of what had happened to her. He crossed the path of the Great Bear in the forest one day, his spear already raised — he had been taught to fear bears. Zeus intervened in the single instant before the spear left Arcas's hand. Both were swept into the sky: Callisto became Ursa Major, Arcas became Boötes the guardian, and the sky arranged itself so that Arcas circles his mother for all eternity, his bright star Arcturus burning behind her. Hera, still angry, persuaded Tethys and Oceanus never to allow the two bears to sink below the horizon and rest.",
    "cast": ["Boötes", "Ursa Major", "Ursa Minor"]
  },
  {
    "id": "orion-al-jabbar",
    "title": "Al-Jabbar, the Giant",
    "text": "Arab astronomers called Orion's brightest stars al-Jabbar — the Giant — and constructed a figure quite different from the Greek hunter. The three belt stars were known as the String of Pearls or the Beam of the Scales. Medieval Arab star-catalogues preserved the names we still use: Betelgeuse from Ibt al-Jauza, armpit of the central one; Rigel from Rijl al-Jauza, foot of the central one. Some early traditions saw the central figure as a woman, al-Jauza, before later astronomy settled on the male giant. The constellation marked the beginning of winter in Arabic astronomical calendars and its rising was used to time the planting of certain crops.",
    "cast": ["Orion"]
  },
  {
    "id": "scorpius-girtablullu",
    "title": "Girtablullu, the Scorpion-Man",
    "text": "The Babylonians knew Scorpius as the place of the scorpion-men, the Girtablullu, guardians who stood at the entrance to the underworld in the Epic of Gilgamesh. Their heads touched the sky and their feet reached the underworld; they guarded the mountain passes at the edge of the world where the sun sets each evening. When Gilgamesh came to them on his quest for immortality after the death of his friend Enkidu, he had to persuade them to let him pass through the tunnel beneath the mountains where the sun travels at night. The heart of the Scorpion — the red star Antares — was the brightest object in the southern midsummer sky and marked the summer solstice region in the oldest Babylonian star lists.",
    "cast": ["Scorpius"]
  },
  {
    "id": "taurus-bull-of-heaven",
    "title": "The Bull of Heaven",
    "text": "In the Babylonian Epic of Gilgamesh, the goddess Ishtar fell in love with the hero and was rejected. Furious, she demanded her father Anu send the Bull of Heaven to destroy him and his friend Enkidu. The bull stamped three times and the earth opened; hundreds of men fell into the pits, and its breath was a whirlwind. Gilgamesh and Enkidu fought it together: Enkidu seized it by the horns while Gilgamesh drove his sword between the shoulder and the neck. When they killed it, the gods mourned. The bull's heart was placed in the sky as tribute to a creature that had been both weapon and sacrifice.",
    "cast": ["Taurus"]
  },
  {
    "id": "leo-xuanxiao",
    "title": "The Vermilion Bird of the South",
    "text": "In Chinese celestial tradition, the stars of Leo fall within the domain of the Vermilion Bird, the Zhu Que, guardian of the southern sky. The bright star Regulus was known as Xuanyuan — the Yellow Emperor — a star so important that battles were timed to its movements and the fall of dynasties was read in its dimming. The Chinese lunar mansions passing through this region — Zhang, Xing, and Liu — were assigned to the wings, neck, and beak of the great red bird. When Regulus brightened, it was taken as a sign of military success; when it was dim or accompanied by guest stars, the emperor's astrologers counselled caution.",
    "cast": ["Leo"]
  },
  {
    "id": "orion-lakota-hand",
    "title": "The Hand That Reached Too Far",
    "text": "The Lakota people of the Great Plains saw in Orion's belt and sword the severed hand of a chief who reached too greedily into the spirit world. The formation is the place where the hand fell from the sky, its fingers pointing down. It appears in winter, the season of the long dark, and Lakota winter count calendars often mark its appearance as a signal to begin the ceremonies of the cold months. The story varies by community, but the core image recurs across the Siouan traditions of the northern plains: the reaching hand, the consequence of overreach, the mark left in the stars.",
    "cast": ["Orion"]
  },
  {
    "id": "ursa-major-bier",
    "title": "The Stretcher and the Mourners",
    "text": "The Lakota saw the four bowl-stars of the Great Bear not as a bear but as a burial bier carrying a body, with three mourning figures following behind — corresponding to the three handle-stars. The slowly rotating formation of these stars around the pole was interpreted as a procession of grief traveling through the year. In some traditions the bier carries the body of a great warrior who must be carried through the sky until a particular ceremony releases the soul. The path of the procession, circling without end, means the mourning is not complete — it will continue until the proper rites are performed.",
    "cast": ["Ursa Major"]
  },
  {
    "id": "aquarius-ea",
    "title": "Ea and the Waters of Wisdom",
    "text": "The Babylonians identified the Water-Bearer as Ea, the god of the underground sweet-water ocean called the Abzu. Ea was the wisest of gods, patron of craftsmen, exorcists, and the arts of civilization; his symbol was the flowing streams of water, which represented wisdom poured out into the world. In the myth of Adapa, Ea's human son was summoned before the sky-god Anu but Ea advised him not to eat or drink anything he was offered — not knowing Anu planned to offer him immortality. The waters that Aquarius pours are Ea's wisdom flowing perpetually downward into human affairs. The constellation sat over the region the Babylonians called the Sea, surrounded by other water-figures in a quadrant of sky they interpreted as a great celestial ocean.",
    "cast": ["Aquarius"]
  },
  {
    "id": "sagittarius-pabilsag",
    "title": "Pabilsag, the Ancestral God",
    "text": "Sagittarius corresponds to the Babylonian figure of Pabilsag, whose name means something like chief ancestor. He was depicted as a hybrid creature: a man's torso, a horse's legs, an eagle's tail-feathers, a scorpion's sting at the rear, a dog's head behind his shoulder, and a drawn bow at the front. In Babylonian medical texts, diseases of the head were attributed to him, and rituals to counter his influence invoked the star at the centaur's heart. The Babylonian map of the sky places him in the southern heavens among the figures of the Sea, and his arrow points toward Antares — the heart of the Scorpion — just as the Greek archer aims at the same target.",
    "cast": ["Sagittarius"]
  },
  {
    "id": "hercules-gilgamesh",
    "title": "Gilgamesh, King of Uruk",
    "text": "The Babylonians identified the kneeling figure of Hercules as Gilgamesh himself — the great king of Uruk who was two-thirds divine, the builder of walls, the one who saw all things. He is depicted in the sky kneeling with one foot on the head of the Dragon, and his story is the first great quest narrative we know: the search for the plant of eternal life after the death of his friend Enkidu. He found the plant at the bottom of the sea and lost it immediately to a serpent who shed its skin and became young again. The kneeling figure in the sky is frozen at the moment before the wrestling match begins, or perhaps the moment after the serpent swam away with immortality.",
    "cast": ["Hercules"]
  },
  {
    "id": "lyra-weaving-girl",
    "title": "The Weaving Girl and the Cowherd",
    "text": "Vega, the brightest star of Lyra, is in Chinese tradition the Weaving Girl, Zhinü, a daughter of the Jade Emperor who wove the clouds of heaven. She fell in love with a mortal cowherd and the two were separated by the Milky Way when the Emperor decreed that divine and mortal should not mix. Once each year, on the seventh day of the seventh lunar month, the magpies of the world fly up together to form a bridge across the river of stars so the two can meet. If it rains on that night, the tears are theirs. The festival of Qixi, held on this date, is still celebrated across East Asia as a festival of lovers and of skill in needlework.",
    "cast": ["Lyra"]
  },
  {
    "id": "virgo-chinese-horn",
    "title": "The Horn Star",
    "text": "The star we call Spica, brightest in Virgo, was to Chinese astronomers the first and most important of the twenty-eight lunar mansions: Jiao, the Horn. It marked the spring equinox in early Chinese astronomy, and its position was used to calibrate the entire celestial calendar. The Horn star was the home of the Heavenly Dragon's left horn, the beginning of the great Green Dragon constellation of the east, one of the four mythological beasts that guard the quadrants of the sky. An eclipse of Jiao or the arrival of a comet near it was considered among the worst of all omens for the imperial throne. The Chinese astronomer Liu Xin set Jiao as the zero-point of the heavens in the first century BCE.",
    "cast": ["Virgo"]
  },
  {
    "id": "canis-major-xolotl",
    "title": "The Dog That Guides the Dead",
    "text": "The Aztec dog-god Xolotl was the guide of the dead on their four-year journey through the nine underworld levels to Mictlan. Hairless and deformed like a lightning bolt, Xolotl was also the god of twins and the evening star. When the sun descended each night into the underworld, it was Xolotl who guided it safely through the darkness to rise again in the east. The bright star Sirius — Mamalhuaztli to the Aztecs, the fire-drill — was watched carefully for its morning rising, which the Aztec solar calendar used to calibrate one of its great cycle counts. The dog among the stars was the escort of the dead and the guardian of the nighttime sun.",
    "cast": ["Canis Major"]
  },
  {
    "id": "scorpius-citlaltlachtli",
    "title": "The Star Ball-Court",
    "text": "The Aztec name for the Scorpius region of the sky was Citlaltlachtli — the Star Ball-Court — because the tail of the constellation curving upward into the Milky Way resembled the I-shaped court of the sacred ball game. The Pleiades and Scorpius were the two key figures in the Aztec Calendar Round count that aligned the 260-day ritual calendar with the 365-day solar year. Their positions in the sky at the first hour of the night on the first day of the solar year determined whether the fire-new ceremony could proceed; if the Pleiades passed the zenith successfully, the world would continue for another 52-year cycle. The heart of the Scorpion — Antares — was associated with the sacrificial fire lit at the center of the ball court.",
    "cast": ["Scorpius"]
  },
  {
    "id": "andromeda-maori",
    "title": "The Net of Māui",
    "text": "Māori navigation placed importance on star formations quite different from those of European tradition, using the entire sky as a compass for deep-sea voyaging across the Pacific. In some traditions the stars of the northern sky, including the Andromeda region, form part of the great net of Māui, the demigod who fished up the North Island of New Zealand. The faint smear of light in this region that can be seen on dark nights — the Andromeda Galaxy — was noticed by Māori astronomers and considered evidence that the sea of stars extended further than the visible band of the Milky Way. Navigators used latitude and the whole sky dome to determine their position and their destination.",
    "cast": ["Andromeda"]
  }
]
```

- [ ] **Step 2: Validate JSON is well-formed**

```bash
python3 -c "import json; d=json.load(open('data/myths.json')); print(len(d), 'myths')"
```

Expected: `46 myths`

- [ ] **Step 3: Run tests**

```bash
.venv/bin/python -m pytest -v
```

Expected: 63 passed (tests mock `pick_constellation_myth` — content changes do not affect them).

- [ ] **Step 4: Commit**

```bash
git add data/myths.json
git commit -m "feat(data): expand myth texts to paragraphs; add 15 non-Greek myths"
```

---

### Task 7: `dark_folklore.json` — expand horror pool

**Files:**
- Modify: `data/dark_folklore.json`

**Interfaces:**
- Produces: nothing consumed by other tasks (tests mock `pick_default_folklore`)

- [ ] **Step 1: Append 30 new entries to `data/dark_folklore.json`**

The file is a JSON array. Add these entries to the existing 20, keeping all current entries intact:

```json
[
  ... (all existing 20 entries unchanged) ...,
  {
    "id": "obayifo",
    "title": "The Obayifo",
    "culture": "Akan (Ghana)",
    "text": "The obayifo is a witch who leaves her body at night, flying as a ball of light through the darkness to find sleeping children. She does not kill outright but drains them slowly — a child who grows pale and listless over many nights, whose crops wither in the same season, may be sustaining an obayifo without knowing it. The light she travels in is her own life-force made visible, and to see it crossing the sky after midnight is to know someone in the village is under attack. Iron placed under a child's sleeping mat is one of the few protections the old knowledge offers."
  },
  {
    "id": "pishtaco",
    "title": "The Pishtaco",
    "culture": "Quechua (Andes)",
    "text": "The pishtaco is a pale stranger who appears on mountain roads and in market towns, offering help or company to travellers who fall behind their group. He carries a blade of exceptional sharpness and is not after blood but after fat — the rendered human fat he needs for machinery, for churches, for purposes that have never been fully explained. Those who survive describe waking in a ditch with a wound so precise it does not hurt until much later, and a heaviness in their limbs that does not leave for months. In the high Andean communities, travellers still warn each other not to accept company from those they do not know."
  },
  {
    "id": "taniwha",
    "title": "The Taniwha",
    "culture": "Māori (New Zealand)",
    "text": "Taniwha are great beings of river, lake, and sea — some are protectors of specific clans, binding agreements to the land's geography; others are predators who drown fishermen and capsize canoes. They shift shape between the form of a log drifting in the current, a shark, a whale, or something with no name at all. A river that has claimed many lives is presumed to have a taniwha that has not been properly acknowledged. The correct approach is not to fight but to negotiate — to speak the right words at the water's edge and establish a relationship that makes passage possible. Those who ignore this do not often get a second opportunity."
  },
  {
    "id": "night-marchers",
    "title": "The Night Marchers",
    "culture": "Hawaiian",
    "text": "On certain nights — particularly those corresponding to the phases of the moon held sacred by the old religion — the spirits of ancient Hawaiian warriors march in procession across the islands, following paths their feet wore into the earth centuries ago. They carry torches; their drums can be heard before they are seen; the smell of decay precedes them. Anyone who looks upon them directly, or who crosses their path, dies. The only exceptions are those whose own ancestors march in the procession — recognising their descendant, they will pass over them. The instruction passed down for centuries is simple: if you hear the drums at night, lie flat, face down, do not look, and do not move."
  },
  {
    "id": "phi-krasue",
    "title": "Phi Krasue",
    "culture": "Thai",
    "text": "The phi krasue is a woman's head that separates from its body at dusk, trailing luminous organs beneath it as it drifts through the night in search of blood and matter that living people would prefer not to name. By day she appears entirely normal; only at night does she reveal what she has become, either through a curse, a magical practice gone wrong, or a punishment whose terms have never been clearly stated. She is most dangerous to pregnant women and to newborns, and the light she emits in darkness is not beautiful but cold. Those who see the glow moving below the treeline have learned not to follow it to find the source."
  },
  {
    "id": "leak",
    "title": "The Leak",
    "culture": "Balinese (Indonesia)",
    "text": "In Balinese tradition, a leak is a sorcerer or sorceress who has learned a dark form of transformation: at night they remove their head, leaving the body behind, and fly through the darkness with their organs trailing, searching for prey. They feed on foetuses and the newly dead, and they can take the shapes of demons, balls of fire, or animals of unusual size. They are not always strangers — the leak in the old stories is often a neighbour, a relative, someone whose grief or desire or rage turned inward and corrupted over many years. A fire left burning overnight and the smell of certain flowers are the traditional deterrents, but no one has ever claimed they are reliable."
  },
  {
    "id": "bunyip",
    "title": "The Bunyip",
    "culture": "Aboriginal Australian",
    "text": "The bunyip lives in the billabongs and waterholes of the Australian interior, in the still dark water beneath the reeds. It bellows in the night — a sound described by those who have heard it as unlike any animal and unlike any human voice — and those who go to investigate the sound at the water's edge rarely return. Its appearance is not fixed in the old knowledge: it is sometimes described as having fur, sometimes feathers, sometimes neither, as if its true form resists description. The waterholes it inhabits are not cursed; they are simply occupied. The appropriate response to finding one has always been to leave before dark."
  },
  {
    "id": "al-demon",
    "title": "The Al",
    "culture": "Persian",
    "text": "The Al is a demon specifically hostile to women in childbirth and to newborns, a thing of iron teeth and claws of brass that enters the birth room when the women's attention is elsewhere. It steals the liver of the mother or the breath of the child; the signs are a sudden collapse with no visible cause, a child who was breathing and then is not. Iron is the universal protection — nails driven into doorframes, scissors left open beside the bed, a knife kept within reach — but the Al can only be stopped by iron it has not already touched. In the oldest texts it is described as having been present at the first birth and is not expected to stop.",
    "culture": "Persian"
  },
  {
    "id": "ghoul",
    "title": "The Ghoul",
    "culture": "Arabian",
    "text": "The ghoul haunts burial grounds and the roads between towns after dark, taking the shape of whatever it last consumed. It is patient in a way that living creatures are not — it will wait for days beside a corpse before eating, simply watching, as if it finds something of value in the process of decay. Travellers who meet a beautiful woman at a crossroads in the desert at night are advised to consider the possibility that she is a ghoul who has recently eaten well. The name became the term for a specific category of being across many traditions: the thing that feeds on the dead, that is neither demon nor spirit nor animal, that exists in the margin between life and what comes after."
  },
  {
    "id": "alux",
    "title": "The Alux",
    "culture": "Maya (Mexico)",
    "text": "The aluxob are small beings — knee-high, or smaller, depending on who is telling — that are called into existence through clay figures and a specific set of rituals, then assigned to guard a particular field or piece of land. They are neither good nor evil but they are exact: they expect offerings and acknowledgment, and they hold to the terms of the agreement with a rigidity that humans often forget and regret. A field whose alux has been neglected does not simply stop producing; the alux begins to work against the farmer — spoiling crops, waking the family at night with sounds that cannot be located, making animals ill. The only resolution is to build a small house for the alux and resume the offerings, which it may or may not choose to accept."
  },
  {
    "id": "camazotz",
    "title": "Camazotz",
    "culture": "Maya",
    "text": "Camazotz is the bat deity of death in the Maya underworld, one of the lords of Xibalba who rules the House of Bats, a place of total darkness through which the dead hero twins Hunahpu and Xbalanque were forced to travel. The name means death bat or snatch bat; his weapon is a stone knife shaped like a crescent blade. When Hunahpu put his head outside the blowgun tube he was hiding in, Camazotz decapitated him in a single movement. The head was used as the ball in the next day's game against the lords of the underworld, until Xbalanque recovered it with the help of a turtle he had substituted in its place. Bats are still associated in Mesoamerican tradition with the movement between the living world and what lies beneath it."
  },
  {
    "id": "supay",
    "title": "Supay",
    "culture": "Inca (Andes)",
    "text": "Supay was the lord of the Incan underworld, Ukhu Pacha, which lay beneath the surface of the earth and received the dead. He was not purely malevolent in the pre-colonial understanding — he was simply the one who governed the lower world, as the sun governed the upper — but the Spanish missionaries found it convenient to identify him with the Christian devil and the name absorbed that meaning over the colonial centuries. In the oldest Quechua traditions, Supay required acknowledgment and tribute like any great lord; the dead who arrived with the proper preparations were received and given a place. Those who arrived without them found a different reception. The threshold between his world and ours is open in certain places, on certain nights, and things pass both ways through it."
  },
  {
    "id": "liderc",
    "title": "The Lüdérc",
    "culture": "Hungarian",
    "text": "The lüdérc hatches from a black hen's egg kept warm under the armpit for the required number of days — the exact number varies by region. What emerges is small and may take the form of a person or of a light, and it attaches itself to its owner with total devotion, bringing them gifts and money in exchange for companionship and, eventually, their life. The lüdérc is never satisfied; it comes at night and cannot be refused, and the host grows thinner and paler with each visit while the creature grows more substantial. The only way to be rid of it is to give it an impossible task — counting every grain in a sack of millet before dawn — after which it is obliged to leave. It does not take rejection well."
  },
  {
    "id": "karabasan",
    "title": "The Karabasan",
    "culture": "Turkish",
    "text": "The karabasan — the dark one that presses down — comes in the hours between sleep and waking when the body cannot move but the mind is entirely present. It takes the form of something heavy sitting on the chest, a weight that is not weight, a presence that is not quite visible at the corner of the eye. Those who have felt it describe not pain but an absolute certainty that whatever is sitting on them has been sitting on people in this precise way since before any city was built. Protective objects placed near the bed — certain verses written on paper, iron, the smell of coffee — are said to discourage it, but the karabasan has been there longer than any of those measures and returns at its own discretion."
  },
  {
    "id": "jiangshi",
    "title": "The Jiangshi",
    "culture": "Chinese",
    "text": "The jiangshi is a corpse that rises from the grave with its arms extended and its body stiff, hopping through the night because rigor mortis has locked its joints into the position they held at death. It drains the life force — qi — from the living through their breath, and those it reaches first will not be found until morning. It cannot smell; it hunts by sensing the breath of the living, which is why those who encounter one in darkness are instructed to hold their breath completely until it passes. Yellow paper inscribed with the correct characters and pasted to the jiangshi's forehead is the classical method of stopping one. The word for it passed into the language long before any of the current methods were devised."
  },
  {
    "id": "empusa",
    "title": "The Empusa",
    "culture": "Greek",
    "text": "The empusa was sent by Hecate to the crossroads where roads met and directions were uncertain, taking the shape of a beautiful young woman, or of a dog, or of a cow with one brass leg and one leg of dung. She approached travellers at night, particularly young men travelling alone, and the seduction was not always visible for what it was until it was complete. Her purpose was consumption — she fed on blood and flesh and the particular vitality of the young. The only method of dispersal described in the ancient sources is to shout at her with insults — she was said to flee from mockery — but those who have recorded this note that it must have seemed at the time like an extremely poor idea."
  },
  {
    "id": "each-uisge",
    "title": "The Each-uisge",
    "culture": "Scottish",
    "text": "The each-uisge — the water horse — rises from the Scottish lochs in the form of a magnificent grey horse, grazing calmly beside the shore as if it belongs there. A rider who mounts it will find they cannot dismount — their hands adhere to its hide, their legs lock against its sides — and the horse walks into the water without pausing. Only the liver floats up the following day. The each-uisge can also take the form of a handsome young man who courts women who live alone near water; the sign that something is wrong is wet sand in his hair, which he cannot entirely conceal. The lochs it inhabits are deep and cold and have not been properly surveyed."
  },
  {
    "id": "hwch-ddu-gwta",
    "title": "Hwch Ddu Gwta",
    "culture": "Welsh",
    "text": "The Hwch Ddu Gwta — the Black Sow with No Tail — pursues stragglers on the night of Calan Gaeaf, the Welsh winter's eve. Bonfires were lit on hilltops and the community gathered around them; when the fire burned low, everyone ran for home together, because to be the last one left at the fire was to be taken. The sow is not seen until she is almost upon you, which is the point: she comes from behind, from the dark that exists between the fire and the door, and those she takes are not found. Children in Wales were told this story not as a horror story but as a practical instruction — stay with the group, keep moving, do not look back."
  },
  {
    "id": "mora",
    "title": "The Mora",
    "culture": "Serbian",
    "text": "The mora is the spirit of a woman who has died and returns in the form of a black moth, a black fly, or a strand of hair that slips through a keyhole to settle on the chest of a sleeping person and press the breath from them. The victim wakes gasping and sweating, aware that something was there, uncertain whether it was a dream. Prolonged visits from a mora result in exhaustion and eventual death; the creature does not hurry because it does not need to. Red thread tied across the doorway, a broom laid crosswise on the threshold, and a knife left open are the traditional deterrents — the mora must count every straw in the broom before entering, and by dawn it must return to wherever it sleeps."
  },
  {
    "id": "gwisin",
    "title": "The Gwisin",
    "culture": "Korean",
    "text": "The gwisin is the ghost of a person who died with unresolved business — an injustice unaddressed, a relationship uncompleted, a death that came too suddenly for any preparation. They haunt the location where they died, or the person most connected to their grievance, and they do not rest until something is resolved or until someone is destroyed trying to provide that resolution. They appear as the person looked in life, often in white funeral clothes, and they are recognisable to those who knew them — which is part of the difficulty. Ignoring a gwisin does not make it leave; it makes it more insistent. The traditional resolution involved a shaman, a ritual, and a negotiation whose terms the gwisin itself had to agree to."
  },
  {
    "id": "churel",
    "title": "The Churel",
    "culture": "Indian",
    "text": "A woman who dies during childbirth or during the festival of Diwali, particularly if she has been mistreated by her husband's family, may return as a churel — a spirit with her feet reversed, heels facing forward, who walks backward through the world. She targets the male relatives of the household where she suffered, luring them away from company at night with an appearance of beauty that is correct in every detail except the feet, which those who know the stories check for first. Those she takes grow old overnight and are found in the morning with their life already used up. The rituals performed at a difficult death are partly for the deceased and partly for the living who remain in the house."
  },
  {
    "id": "yara-ma-yha-who",
    "title": "The Yara-ma-yha-who",
    "culture": "Aboriginal Australian",
    "text": "The yara-ma-yha-who is a small red man who lives in fig trees and drops onto those who rest in the shade below, fastening the suckers on his hands to the victim's skin and drawing out the blood. When he has fed he swallows the person whole, drinks water, sleeps, and regurgitates them — alive, but shorter than before. Those who are taken multiple times are eventually regurgitated as a yara-ma-yha-who themselves. The way to survive the encounter is to remain limp and appear dead during the process; an active victim is more interesting to it, a passive one is more likely to be left after the first or second time. The stories are told to children who must learn to rest carefully and to choose their shade tree with attention."
  },
  {
    "id": "qalupalik",
    "title": "The Qalupalik",
    "culture": "Inuit",
    "text": "The qalupalik lives beneath the sea ice and makes a humming sound that rises through the frozen surface on cold days — a sound children are warned not to follow to the edge. It has green skin, long fingernails, and carries an amauti, the traditional child-carrying pouch, into which it places children who disobey their parents or who wander too close to the ice edge alone. What happens to them beneath the ice is not described in detail because the point of the story is the warning, not the outcome. The ice is the boundary between the world that can sustain life and the world that cannot, and the qalupalik is what waits on the other side of that boundary for those who do not take it seriously."
  },
  {
    "id": "stikini",
    "title": "The Stikini",
    "culture": "Muscogee (Oklahoma)",
    "text": "The stikini is a person who transforms at night by vomiting out their organs, leaving them temporarily stored in a hollow tree, before taking the form of a great horned owl and flying to find sleeping humans whose hearts it can extract and eat. The person appears entirely normal during the day — the neighbours do not know, which is the point. The way to destroy a stikini is to find the hidden organs before the creature returns and salt them or expose them to sunlight; when the stikini tries to resume its human form and finds its organs ruined, it dies. The sound of a great horned owl calling near a house at night was, in the old tradition, not a neutral observation about wildlife."
  },
  {
    "id": "sigbin",
    "title": "The Sigbin",
    "culture": "Philippine Visayan",
    "text": "The sigbin walks backward with its head lowered between its legs, releasing a foul smell that travels ahead of it through the dark. It feeds first on shadow — it drains the shadow of a sleeping person, which they do not notice until they are already weakened — and then on blood. Witches keep sigbin as familiars in clay pots sealed with beeswax, releasing them at night to do their work and recalling them before dawn. A person who has had their shadow stolen grows thin and cold over weeks; the recovery, if it is possible, requires locating the sigbin's jar and breaking it, which is difficult to do without knowing whose house to search. The sigbin is most active during Holy Week, which is one of the details that makes it particularly unsettling to those for whom that period carries other significance."
  },
  {
    "id": "gjenganger",
    "title": "The Gjenganger",
    "culture": "Norwegian",
    "text": "The gjenganger is the revenant of a person who died violently, by suicide, or without proper Christian burial — the one whose unfinished existence drives them back into the world of the living. Unlike the draugr, the gjenganger looks entirely human during the day, and its most characteristic action is small: it pinches the living on the arm or shoulder while they sleep, leaving a blue bruise. The bruise is not the injury; the injury is the illness that follows — a wasting sickness that looks like nothing diagnosable and ends, weeks later, in death. The gjenganger spreads its condition from person to person through touch, and an outbreak could move through a household before anyone understood the pattern. The blue marks on the skin of the dying were the diagnostic sign."
  },
  {
    "id": "duppy",
    "title": "The Duppy",
    "culture": "Jamaican",
    "text": "When a person dies, two spirits leave the body: one ascends to face judgment and the other — the duppy — remains near the grave for three days before it can be made to depart. If the burial was improper, if a grievance was left unresolved, or if someone with knowledge of the old practices summons it, the duppy does not depart and becomes dangerous: it can be sent against enemies, it can drive people mad, it can cause accidents. The traditional deterrents involve rum poured at the grave and certain tobacco rituals, but these negotiate with the duppy rather than destroy it — the understanding is that you are acknowledging it has legitimate claims and you are asking it to choose otherwise. Most duppies do. The ones that do not are a different matter."
  },
  {
    "id": "loup-garou",
    "title": "The Loup-garou",
    "culture": "Haitian and Cajun",
    "text": "The loup-garou sheds their skin at night, leaving it carefully folded in a hidden place, and ranges through the darkness as a fireball or as an animal of unusual size, feeding on whatever they need to sustain the transformation. The way to stop one is to find the skin before dawn and rub it with salt; when the loup-garou tries to put it back on, the salt burns and the creature is destroyed. But finding the skin requires knowing where the person has hidden it, which requires knowing who the loup-garou is, which is the difficulty — they are always neighbours, always someone whose face you know in daylight. In Cajun country the condition was considered both a curse and a punishment for specific sins, and the number of years one must range before being released was fixed and known."
  },
  {
    "id": "almas",
    "title": "The Almas",
    "culture": "Mongolian",
    "text": "The almas walks the high mountain passes of Central Asia, covered in reddish hair, humanoid but not human, and it is said to know in advance the names of those who will die in the coming winter — something it acquired not through any supernatural power but through long observation of the world that the living have not learned to read. Those who have encountered one and survived describe a creature that did not attack but watched with an attention that felt like inventory. Nomadic communities in the Altai and the Mongolian highlands have included the almas in their understanding of what shares the landscape with them for long enough that it has ceased to be simply a monster in their telling and has become something more like a neighbour that it is wise not to disturb."
  }
]
```

- [ ] **Step 2: Verify JSON and count**

```bash
python3 -c "import json; d=json.load(open('data/dark_folklore.json')); print(len(d), 'entries')"
```

Expected: `50 entries`

- [ ] **Step 3: Run tests**

```bash
.venv/bin/python -m pytest -v
```

Expected: 63 passed (tests mock `pick_default_folklore` — content changes do not affect them).

- [ ] **Step 4: Commit**

```bash
git add data/dark_folklore.json
git commit -m "feat(data): expand dark folklore pool to 50 entries across global cultures"
```

---

## Self-Review

**Spec coverage:**
- ✅ `dark_folklore.json` expand to ~50, horror prose, global cultures → Task 7
- ✅ `myths.json` richer paragraph texts + non-Greek myths → Task 6
- ✅ `myth_art.json` alt_categories + search_terms → Task 4
- ✅ `mythart.py` 5-strategy lookup → Task 5
- ✅ `skymap.py` cold palette → Task 2
- ✅ `app.js` marker polish → Task 3
- ✅ Wordmark rename → Task 1

**Placeholder scan:** No TBDs. All JSON content is complete. All code blocks are complete.

**Type consistency:**
- `_fetch_art(category, name, alt_categories, search_terms)` — called exactly this way in Task 5 step 3 and asserted this way in the test in Task 5 step 1 ✅
- `_search_titles(query)` — now takes raw query string, old `_search_titles(name)` call is replaced by `_search_titles(f"{name} constellation mythology art")` in generic fallback ✅
- `_MYTH_ART` loaded at module level — referenced consistently in `get_constellation_art` and in the test mock ✅

**Cast constraint:** All cast values in Task 6 myths checked against the 20 constellation names in Global Constraints ✅
