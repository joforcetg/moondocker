# Legends, Constellation Myths & Sky Highlight — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the legend panel show dark world-folklore by default and a daily-fixed constellation myth (with live classical artwork + sky highlight) when a constellation card is clicked, plus next-moon-phase dates and a gothic/monochrome visual refresh.

**Architecture:** Backend adds two pure picker functions + an almanac lookup in `astronomy.py`, an isolated Wikimedia client in a new `mythart.py`, and one new endpoint in `main.py`; the `/api/sky` `mythology` field is renamed to `legend`. Frontend (vanilla JS/CSS) rewires the legend/cards, draws the moon as an SVG, and highlights constellations in the inline sky-map SVG. New curated data files replace `mythology.json`.

**Tech Stack:** Python 3 · FastAPI · skyfield · stdlib `urllib` (no new deps) · vanilla JS · CSS · pytest.

## Global Constraints

- All Python commands use `.venv/bin/python` (system Python lacks deps).
- No new Python dependency — Wikimedia client uses stdlib `urllib`.
- No JS framework, bundler, or build step. Vanilla JS served from `/static`.
- No web-font CDN — fonts are bundled woff2 in `app/static/fonts/`, SIL OFL.
- Test mocks patch `app.main.*` bindings (because `main.py` uses
  `from .astronomy import …`). If you add an import to `main.py`, patch the
  `app.main.*` name, not the source module.
- All user-facing strings injected from JS stay `esc()`'d or set via
  `textContent`. SVG is injected via `DOMParser` + `importNode`, never raw
  `innerHTML` of untrusted strings.
- Constellation `name` values are the canonical key everywhere (cards, myth
  cast, `data-constellation`, `myth_art.json`) — taken from
  `data/constellations.json` (e.g. `Orion`, `Ursa Major`, `Boötes`).
- Candlelit Grimoire mood kept; palette pushed toward near-monochrome with
  candle-gold (`#d0a24a`) and oxblood used only as sparse accents.
- Commit after every task with the shown message.

---

## File Structure

**Data (create):**
- `data/dark_folklore.json` — default legend pool.
- `data/myths.json` — constellation myths with role-ordered `cast`.
- `data/myth_art.json` — constellation → Wikimedia Commons category.
- `data/mythology.json` — **delete** (superseded).

**Backend (modify/create):**
- `app/astronomy.py` — add next-phase fields; replace `pick_mythology` with
  `pick_default_folklore` + `pick_constellation_myth`; add `constellation` to
  `const_lines`.
- `app/skymap.py` — tag lines/stars with `data-constellation`; monochrome colors.
- `app/mythart.py` — **create**: Wikimedia client + cache.
- `app/main.py` — load new data; `/api/sky` `legend` + `has_myth` + moon
  passthrough; new `GET /api/myth/{constellation}`.

**Frontend (modify/create):**
- `app/static/index.html` — legend figure container; cards container.
- `app/static/app.js` — legend default, SVG moon, cards + click + highlight.
- `app/static/style.css` — `@font-face`, palette vars, typography, cards,
  figure, highlight, moon styles.
- `app/static/fonts/` — **create**: bundled woff2 files.

**Tests (modify/create):**
- `tests/conftest.py` — update mocks for renamed pickers + `legend` key.
- `tests/test_astronomy.py` — pickers + next-phase.
- `tests/test_skymap.py` — `data-constellation` tagging.
- `tests/test_mythart.py` — **create**: Wikimedia client + cache.
- `tests/test_main.py` — `/api/sky` shape + `/api/myth/{constellation}`.

**Docs:** `CLAUDE.md` — update mock-binding note + architecture.

---

## Task 1: Curated data files

**Files:**
- Create: `data/dark_folklore.json`, `data/myths.json`, `data/myth_art.json`
- Delete: `data/mythology.json`
- Test: `tests/test_data_files.py`

**Interfaces:**
- Produces:
  - `dark_folklore.json`: JSON array of `{"id": str, "title": str, "culture": str, "text": str}`.
  - `myths.json`: JSON array of `{"id": str, "title": str, "text": str, "cast": [str, ...]}` where `cast` is 1–3 constellation names in role order.
  - `myth_art.json`: JSON object `{ "<Constellation Name>": {"category": "Category:..."} }`.

**Content requirements:**
- `myth_art.json` MUST have an entry for each of the 20 constellation names in
  `data/constellations.json`.
- Every constellation name in `myth_art.json` MUST appear in the `cast` of at
  least one `myths.json` entry. Aim for ~30 myths (several constellations share
  myths, e.g. Orion + Scorpius, Perseus + Andromeda + Cassiopeia).
- `dark_folklore.json`: ~20 entries, dark/night/witch/monster tone, varied world
  cultures, NOT constellation-tied. Text is original/paraphrased prose (2–4
  sentences), not copied verbatim from any source.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_data_files.py
import json
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"


def _load(name):
    with open(DATA / name, encoding="utf-8") as f:
        return json.load(f)


def test_folklore_shape():
    items = _load("dark_folklore.json")
    assert len(items) >= 15
    ids = [x["id"] for x in items]
    assert len(ids) == len(set(ids))  # unique ids
    for x in items:
        assert set(x) >= {"id", "title", "culture", "text"}
        assert x["text"].strip()


def test_myths_shape_and_cast():
    myths = _load("myths.json")
    assert len(myths) >= 20
    ids = [m["id"] for m in myths]
    assert len(ids) == len(set(ids))
    for m in myths:
        assert set(m) >= {"id", "title", "text", "cast"}
        assert 1 <= len(m["cast"]) <= 3


def test_every_art_constellation_has_a_myth():
    consts = _load("constellations.json")
    names = {c["name"] for c in consts}
    art = _load("myth_art.json")
    myths = _load("myths.json")
    cast_names = {n for m in myths for n in m["cast"]}
    # art keys must all be real constellations
    assert set(art) <= names
    # every art constellation must be castable
    assert set(art) <= cast_names, set(art) - cast_names


def test_mythology_json_removed():
    assert not (DATA / "mythology.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_data_files.py -v`
Expected: FAIL (files missing / `mythology.json` still present).

- [ ] **Step 3: Author the three data files and delete `mythology.json`**

Create `data/myth_art.json` with all 20 constellation names. Example shape:

```json
{
  "Orion":      { "category": "Category:Orion in art" },
  "Scorpius":   { "category": "Category:Scorpius (constellation) in art" },
  "Andromeda":  { "category": "Category:Andromeda (mythology)" },
  "Perseus":    { "category": "Category:Perseus" },
  "Cassiopeia": { "category": "Category:Cassiopeia (mythology)" }
}
```
(Curate a sensible Commons category per constellation; verify each exists on
commons.wikimedia.org.)

Create `data/myths.json`. Three complete examples (author ~30 total, covering
every constellation in `myth_art.json` at least once):

```json
[
  {
    "id": "orion-scorpius",
    "title": "The Hunter and the Scorpion",
    "text": "Orion boasted he could slay every beast on earth. Gaia sent a scorpion that stung him dead; the two were set in the sky on opposite sides so the hunter still flees as the scorpion rises.",
    "cast": ["Orion", "Scorpius"]
  },
  {
    "id": "perseus-andromeda",
    "title": "The Chained Princess",
    "text": "Cassiopeia's boast doomed her daughter Andromeda to the sea-monster Cetus. Perseus, still carrying the Gorgon's head, turned the beast to stone and freed her.",
    "cast": ["Perseus", "Andromeda", "Cassiopeia"]
  },
  {
    "id": "callisto-bears",
    "title": "The Bear Mother",
    "text": "Callisto was changed into a bear and nearly slain by her own son before Zeus cast them both into the sky as the Great and Little Bears, circling forever without rest.",
    "cast": ["Ursa Major", "Ursa Minor", "Boötes"]
  }
]
```

Create `data/dark_folklore.json`. Two complete examples (author ~20 total):

```json
[
  {
    "id": "wendigo",
    "title": "The Wendigo",
    "culture": "Algonquian",
    "text": "A gaunt spirit of insatiable winter hunger is said to walk the frozen forests, growing taller the more it devours. To hear it call your name across the snow is to be already lost."
  },
  {
    "id": "la-llorona",
    "title": "La Llorona",
    "culture": "Mexican",
    "text": "By night a weeping woman drifts along the water's edge, mourning the children she drowned. Those who follow her cries to the river are seldom seen at dawn."
  }
]
```

Delete the old file:

```bash
git rm data/mythology.json
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_data_files.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add data/dark_folklore.json data/myths.json data/myth_art.json tests/test_data_files.py
git add -u data/mythology.json
git commit -m "feat: add folklore + constellation-myth data, retire mythology.json"
```

---

## Task 2: Folklore + constellation-myth pickers

**Files:**
- Modify: `app/astronomy.py` (replace `pick_mythology`)
- Test: `tests/test_astronomy.py`

**Interfaces:**
- Consumes: `dark_folklore.json` list, `myths.json` list (loaded by caller).
- Produces:
  - `pick_default_folklore(folklore: list[dict], date_str: str | None = None) -> dict`
    → returns a folklore entry dict (`id,title,culture,text`), daily-deterministic.
  - `pick_constellation_myth(name: str, myths: list[dict], date_str: str | None = None) -> dict | None`
    → `{"constellation": name, "title": str, "text": str}` or `None` if no myth
    has `name` in its `cast`. Eligible pool ordered by role (myths where `name`
    is `cast[0]` first, then `cast[1]`, then `cast[2]`); daily-deterministic pick
    within that ordered pool.

- [ ] **Step 1: Write the failing tests**

```python
# add to tests/test_astronomy.py
from app.astronomy import pick_default_folklore, pick_constellation_myth

_FOLK = [
    {"id": "a", "title": "A", "culture": "x", "text": "ta"},
    {"id": "b", "title": "B", "culture": "y", "text": "tb"},
    {"id": "c", "title": "C", "culture": "z", "text": "tc"},
]
_MYTHS = [
    {"id": "m1", "title": "M1", "text": "t1", "cast": ["Orion", "Scorpius"]},
    {"id": "m2", "title": "M2", "text": "t2", "cast": ["Scorpius"]},
    {"id": "m3", "title": "M3", "text": "t3", "cast": ["Lyra"]},
]


def test_folklore_is_daily_deterministic():
    a = pick_default_folklore(_FOLK, date_str="2026-06-18")
    b = pick_default_folklore(_FOLK, date_str="2026-06-18")
    assert a == b
    assert a in _FOLK


def test_folklore_varies_by_date():
    days = {pick_default_folklore(_FOLK, date_str=f"2026-06-{d:02d}")["id"]
            for d in range(1, 29)}
    assert len(days) > 1  # not stuck on one entry


def test_myth_filters_by_cast_membership():
    m = pick_constellation_myth("Lyra", _MYTHS, date_str="2026-06-18")
    assert m == {"constellation": "Lyra", "title": "M3", "text": "t3"}


def test_myth_none_when_absent():
    assert pick_constellation_myth("Gemini", _MYTHS, date_str="2026-06-18") is None


def test_myth_role_ordering_lead_first():
    # Orion is lead in m1 only; pool=[m1]; Scorpius is lead in m2, second in m1
    assert pick_constellation_myth("Orion", _MYTHS, date_str="2026-06-18")["title"] == "M1"


def test_myth_is_daily_deterministic():
    a = pick_constellation_myth("Scorpius", _MYTHS, date_str="2026-06-18")
    b = pick_constellation_myth("Scorpius", _MYTHS, date_str="2026-06-18")
    assert a == b
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_astronomy.py -k "folklore or myth" -v`
Expected: FAIL with ImportError (`pick_default_folklore` not defined).

- [ ] **Step 3: Implement the pickers**

In `app/astronomy.py`, delete `pick_mythology` and add (reuse the existing
`hashlib`/`_date` imports already at the top of the file):

```python
def _date_seed(date_str: str | None) -> int:
    if date_str is None:
        date_str = _date.today().isoformat()
    return int(hashlib.md5(date_str.encode(), usedforsecurity=False).hexdigest(), 16)


def pick_default_folklore(folklore: list[dict], date_str: str | None = None) -> dict:
    """Pick one dark-folklore entry deterministically by date."""
    seed = _date_seed(date_str)
    return folklore[seed % len(folklore)]


def pick_constellation_myth(
    name: str, myths: list[dict], date_str: str | None = None
) -> dict | None:
    """
    Pick one myth that features `name`, deterministically by date.
    Eligible pool = myths whose cast contains `name`, ordered by the role
    `name` plays (lead first, then second, then third). Returns None if `name`
    is in no myth's cast.
    """
    pool = [m for m in myths if name in m["cast"]]
    if not pool:
        return None
    pool.sort(key=lambda m: m["cast"].index(name))
    seed = _date_seed(date_str)
    chosen = pool[seed % len(pool)]
    return {"constellation": name, "title": chosen["title"], "text": chosen["text"]}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_astronomy.py -k "folklore or myth" -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add app/astronomy.py tests/test_astronomy.py
git commit -m "feat: add folklore and constellation-myth pickers"
```

---

## Task 3: Next moon-phase dates

**Files:**
- Modify: `app/astronomy.py` (`get_moon_data`)
- Test: `tests/test_astronomy.py`

**Interfaces:**
- Produces: `get_moon_data(...)` return dict gains
  `next_new_date` (str `YYYY-MM-DD` | None), `next_new_in_days` (int | None),
  `next_full_date` (str | None), `next_full_in_days` (int | None).

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_astronomy.py
from unittest.mock import patch
import app.astronomy as astro


def test_next_phase_fields_present():
    # Drive get_moon_data with a real timescale but mocked almanac search so we
    # don't need ephemeris files. We patch the helper that computes next phases.
    fake = {
        "next_new_date": "2026-06-25", "next_new_in_days": 7,
        "next_full_date": "2026-07-09", "next_full_in_days": 21,
    }
    with patch.object(astro, "_next_phase_dates", return_value=fake):
        # _next_phase_dates is called inside get_moon_data; everything else that
        # needs ephemeris is exercised by existing get_moon_data tests, so here
        # we only assert the merge. Call the small helper directly:
        assert astro._next_phase_dates is not None
        out = astro._merge_next_phases({"phase_name": "Full Moon"}, fake)
        assert out["next_full_in_days"] == 21
        assert out["next_new_date"] == "2026-06-25"
```

> Note: This task introduces two small helpers so the almanac search is testable
> without ephemeris files: `_next_phase_dates(ts, eph, t)` (does the skyfield
> work) and `_merge_next_phases(moon_dict, phases)` (pure merge). Existing
> `get_moon_data` tests that mock skyfield continue to pass because the new
> fields default to `None` on failure.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_astronomy.py -k next_phase -v`
Expected: FAIL (`_merge_next_phases` not defined).

- [ ] **Step 3: Implement the helpers and wire them in**

In `app/astronomy.py` add:

```python
def _merge_next_phases(moon: dict, phases: dict) -> dict:
    moon.update(phases)
    return moon


_EMPTY_PHASES = {
    "next_new_date": None, "next_new_in_days": None,
    "next_full_date": None, "next_full_in_days": None,
}


def _next_phase_dates(ts, eph, t) -> dict:
    """Next New (event 0) and Full (event 2) moon after t, via skyfield almanac."""
    from skyfield import almanac
    try:
        t1 = ts.tt_jd(t.tt + 40.0)  # one synodic month fits in 40 days
        f = almanac.moon_phases(eph)
        times, events = almanac.find_discrete(t, t1, f)
        out = dict(_EMPTY_PHASES)
        today = t.utc_datetime().date()
        for t_evt, evt in zip(times, events):
            d = t_evt.utc_datetime().date()
            days = (d - today).days
            if evt == 0 and out["next_new_date"] is None:
                out["next_new_date"], out["next_new_in_days"] = d.isoformat(), days
            elif evt == 2 and out["next_full_date"] is None:
                out["next_full_date"], out["next_full_in_days"] = d.isoformat(), days
        return out
    except Exception:
        logger.exception("next moon-phase lookup failed")
        return dict(_EMPTY_PHASES)
```

In `get_moon_data`, just before the final `return { ... }`, compute phases and
merge them into the returned dict. Change the return so it includes the merge —
e.g. build the dict then:

```python
    result = {
        "phase_name":       phase_name,
        "phase_glyph":      phase_glyph,
        "illumination_pct": illumination,
        "rise":             rise_str,
        "set":              set_str,
        "transit":          transit_str,
        "note":             polar_visibility_note(rise_str, set_str, transit_alt),
    }
    return _merge_next_phases(result, _next_phase_dates(ts, eph, t))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_astronomy.py -k next_phase -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/astronomy.py tests/test_astronomy.py
git commit -m "feat: compute next new/full moon dates"
```

---

## Task 4: Tag constellation on sky-map line segments

**Files:**
- Modify: `app/astronomy.py` (`get_skymap_stars`)
- Test: `tests/test_astronomy.py`

**Interfaces:**
- Produces: `get_skymap_stars(...)` second return value (`const_lines`) entries
  gain `"constellation": str` → `{"hip_a", "hip_b", "constellation"}`.

- [ ] **Step 1: Write the failing test**

The existing skymap-star tests need ephemeris. Instead test the line-building in
isolation by asserting the shape on a constructed call is impractical without
skyfield, so test the pure assembly via a tiny extracted helper.

Add to `app/astronomy.py` a pure helper and test it:

```python
# tests/test_astronomy.py
from app.astronomy import _build_const_lines


def test_const_lines_carry_constellation_name():
    consts = [{"name": "Orion", "lines": [[1, 2], [2, 3]]}]
    hip_above = {1, 2, 3}
    lines = _build_const_lines(consts, hip_above)
    assert {"hip_a": 1, "hip_b": 2, "constellation": "Orion"} in lines
    assert all("constellation" in seg for seg in lines)


def test_const_lines_skip_below_horizon():
    consts = [{"name": "Orion", "lines": [[1, 2], [2, 9]]}]
    lines = _build_const_lines(consts, {1, 2})  # 9 missing
    assert lines == [{"hip_a": 1, "hip_b": 2, "constellation": "Orion"}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_astronomy.py -k const_lines -v`
Expected: FAIL (`_build_const_lines` not defined).

- [ ] **Step 3: Extract the helper and use it**

In `app/astronomy.py`, add:

```python
def _build_const_lines(constellation_data: list[dict], hip_above: set[int]) -> list[dict]:
    lines = []
    for const in constellation_data:
        for hip_a, hip_b in const["lines"]:
            if hip_a in hip_above and hip_b in hip_above:
                lines.append({"hip_a": hip_a, "hip_b": hip_b, "constellation": const["name"]})
    return lines
```

In `get_skymap_stars`, replace the inline `const_lines` loop (the block building
`const_lines`) with:

```python
    const_lines = _build_const_lines(constellation_data, hip_above)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_astronomy.py -k const_lines -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/astronomy.py tests/test_astronomy.py
git commit -m "feat: tag sky-map segments with constellation name"
```

---

## Task 5: Monochrome sky map + data-constellation tagging

**Files:**
- Modify: `app/skymap.py` (`generate_skymap`)
- Test: `tests/test_skymap.py`

**Interfaces:**
- Consumes: `const_lines` entries now include `"constellation"` (Task 4).
- Produces: SVG where each stick-figure `<line>` has
  `data-constellation="<name>"`, each figure-star `<circle>` has
  `data-constellation="<space-joined names>" class="figstar"`. Background stars
  have no `data-constellation`. Default colors are near-monochrome.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_skymap.py
from app.skymap import generate_skymap


def test_lines_tagged_with_constellation():
    stars = [
        {"alt": 80, "az": 0, "magnitude": 1.0, "hip_id": 1},
        {"alt": 70, "az": 90, "magnitude": 1.0, "hip_id": 2},
        {"alt": 60, "az": 180, "magnitude": 4.0, "hip_id": 9},  # background
    ]
    lines = [{"hip_a": 1, "hip_b": 2, "constellation": "Orion"}]
    svg = generate_skymap(stars, lines)
    assert 'data-constellation="Orion"' in svg
    assert '<line' in svg and 'data-constellation="Orion"' in svg
    # figure stars (1,2) tagged; background star (9) not
    assert svg.count('class="figstar"') == 2
    assert svg.count('data-constellation') == 3  # 1 line + 2 figure stars


def test_no_constellation_attr_on_background_star():
    stars = [{"alt": 60, "az": 180, "magnitude": 4.0, "hip_id": 9}]
    svg = generate_skymap(stars, [])
    assert "data-constellation" not in svg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_skymap.py -k constellation -v`
Expected: FAIL (no `data-constellation` emitted).

- [ ] **Step 3: Implement tagging + monochrome colors**

Replace the body of `generate_skymap` in `app/skymap.py` (keep `az_alt_to_xy`,
`star_radius`, and the module constants) with:

```python
def generate_skymap(stars: list[dict], const_lines: list[dict]) -> str:
    hip_xy: dict[int, tuple[float, float]] = {
        s["hip_id"]: az_alt_to_xy(s["az"], s["alt"]) for s in stars
    }

    # figure-star membership: hip_id -> sorted set of constellation names
    fig_members: dict[int, set[str]] = {}
    lines_svg = []
    for seg in const_lines:
        a, b, name = seg["hip_a"], seg["hip_b"], seg["constellation"]
        if a in hip_xy and b in hip_xy:
            x1, y1 = hip_xy[a]
            x2, y2 = hip_xy[b]
            lines_svg.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'data-constellation="{name}" '
                f'stroke="#6b6256" stroke-width="0.8" stroke-opacity="0.7"/>'
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
                f'fill="#ece7da" fill-opacity="0.95"/>'
            )
        else:
            stars_svg.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" '
                f'fill="#cfc8b8" fill-opacity="0.85"/>'
            )

    cardinals = [("N", 0), ("E", 90), ("S", 180), ("W", 270)]
    cardinal_svg = []
    for label, az in cardinals:
        x, y = az_alt_to_xy(az, 0.0)
        scale = (R + 12) / R
        lx = CX + (x - CX) * scale
        ly = CY + (y - CY) * scale
        cardinal_svg.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" fill="#8a8276" font-size="10" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'font-family="serif">{label}</text>'
        )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {VIEWBOX_SIZE} {VIEWBOX_SIZE}" '
        f'width="{VIEWBOX_SIZE}" height="{VIEWBOX_SIZE}" style="background:#08080a">',
        f'<circle cx="{CX:.1f}" cy="{CY:.1f}" r="{R:.1f}" fill="#08080a" '
        f'stroke="#2a2a2e" stroke-width="1"/>',
        *lines_svg,
        *stars_svg,
        *cardinal_svg,
        "</svg>",
    ]
    return "\n".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_skymap.py -v`
Expected: PASS (new + existing). If existing tests asserted old hex colors,
update those assertions to the new monochrome values.

- [ ] **Step 5: Commit**

```bash
git add app/skymap.py tests/test_skymap.py
git commit -m "feat: monochrome sky map with data-constellation tagging"
```

---

## Task 6: Wikimedia artwork client + cache

**Files:**
- Create: `app/mythart.py`
- Test: `tests/test_mythart.py`

**Interfaces:**
- Produces:
  - `get_constellation_art(name: str, category: str) -> dict | None`
    → `{"url", "title", "author", "license", "credit_url"}` or `None`.
    Cached per `name` with a 7-day TTL; failures return `None` and are not cached.
  - Module attr `_CACHE: dict[str, tuple[float, dict]]` and `CACHE_TTL_SECONDS = 7*24*3600`.
  - `_fetch_art(category: str) -> dict | None` (network; mocked in tests).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_mythart.py
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
```

(Add `import pytest` at the top of the test file.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_mythart.py -v`
Expected: FAIL (module `app.mythart` missing).

- [ ] **Step 3: Implement `app/mythart.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_mythart.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add app/mythart.py tests/test_mythart.py
git commit -m "feat: Wikimedia artwork client with 7-day cache"
```

---

## Task 7: API wiring — `legend`, `has_myth`, `/api/myth/{constellation}`

**Files:**
- Modify: `app/main.py`, `tests/conftest.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `pick_default_folklore`, `pick_constellation_myth` (Task 2),
  `get_constellation_art` (Task 6).
- Produces:
  - `/api/sky` returns `legend` (folklore dict) instead of `mythology`; each
    `constellations[]` entry has `has_myth: bool`; moon carries next-phase fields.
  - `GET /api/myth/{constellation}` → `{constellation, title, text, image}`
    (`image` is the art dict or `null`); unknown name → 404.

- [ ] **Step 1: Update conftest, then write failing tests**

Update `tests/conftest.py`:

```python
MOCK_LEGEND = {"id": "x", "title": "The Wendigo", "culture": "Algonquian", "text": "..."}
MOCK_CONSTELLATIONS = [
    {"name": "Orion", "abbr": "Ori", "above_horizon": True, "has_myth": True},
    {"name": "Gemini", "abbr": "Gem", "above_horizon": True, "has_myth": False},
]
```

Replace the `pick_mythology` patch with patches for the new names and add the
constellation `has_myth` enrichment into the mock (since `has_myth` is computed
in `main.py`, the mock for `get_visible_constellations` returns entries WITHOUT
`has_myth`; `main.py` adds it — so drop `has_myth` from `MOCK_CONSTELLATIONS`
and let main.py add it). Final fixture:

```python
@pytest.fixture()
def client():
    with patch("app.main.get_moon_data", return_value=MOCK_MOON), \
         patch("app.main.get_visible_constellations", return_value=[
             {"name": "Orion", "abbr": "Ori", "above_horizon": True},
             {"name": "Gemini", "abbr": "Gem", "above_horizon": True},
         ]), \
         patch("app.main.get_skymap_stars", return_value=([], [])), \
         patch("app.main.generate_skymap", return_value=MOCK_SVG), \
         patch("app.main.pick_default_folklore", return_value=MOCK_LEGEND):
        from fastapi.testclient import TestClient
        from app.main import app
        yield TestClient(app)
```

Add to `tests/test_main.py`:

```python
from unittest.mock import patch


def test_sky_returns_legend_and_has_myth(client):
    r = client.get("/api/sky?lat=40&lon=-74")
    assert r.status_code == 200
    body = r.json()
    assert "legend" in body and "mythology" not in body
    assert body["legend"]["title"] == "The Wendigo"
    has = {c["name"]: c["has_myth"] for c in body["constellations"]}
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
```

> For `has_myth`, `main.py` decides truth by asking
> `pick_constellation_myth(name, MYTHS_DATA) is not None`. In `test_sky_...`
> Orion is in the real `myths.json` cast and Gemini may not be — if Gemini has
> a myth in your authored data, change the assertion to a constellation you did
> not give a myth, or patch `pick_constellation_myth`. Keep the test honest
> against the data you authored in Task 1.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_main.py -v`
Expected: FAIL (`legend` missing / route 404 logic absent).

- [ ] **Step 3: Implement `main.py` changes**

Update imports and data loading:

```python
from .astronomy import (
    get_moon_data,
    get_visible_constellations,
    get_skymap_stars,
    pick_default_folklore,
    pick_constellation_myth,
)
from .skymap import generate_skymap
from .mythart import get_constellation_art
from fastapi import FastAPI, Query, HTTPException
```

Replace the `mythology.json` load with the three new files:

```python
with open(DATA_DIR / "constellations.json") as _f:
    CONSTELLATION_DATA: list[dict] = json.load(_f)
with open(DATA_DIR / "dark_folklore.json", encoding="utf-8") as _f:
    FOLKLORE_DATA: list[dict] = json.load(_f)
with open(DATA_DIR / "myths.json", encoding="utf-8") as _f:
    MYTHS_DATA: list[dict] = json.load(_f)
with open(DATA_DIR / "myth_art.json", encoding="utf-8") as _f:
    MYTH_ART_DATA: dict[str, dict] = json.load(_f)

CONSTELLATION_NAMES = {c["name"] for c in CONSTELLATION_DATA}
```

Rewrite `get_sky`:

```python
@app.get("/api/sky")
async def get_sky(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
) -> dict:
    t           = ts.now()
    moon        = get_moon_data(ts, lat, lon, t=t)
    consts      = get_visible_constellations(ts, lat, lon, CONSTELLATION_DATA, t=t)
    for c in consts:
        c["has_myth"] = pick_constellation_myth(c["name"], MYTHS_DATA) is not None
    legend      = pick_default_folklore(FOLKLORE_DATA)
    stars, segs = get_skymap_stars(ts, lat, lon, CONSTELLATION_DATA, t=t)
    svg         = generate_skymap(stars, segs)

    return {
        "moon":           moon,
        "constellations": consts,
        "skymap_svg":     svg,
        "legend":         legend,
        "computed_at":    t.utc_iso(),
        "location":       {"lat": lat, "lon": lon},
    }
```

Add the new endpoint (above the `app.mount(...)` line):

```python
@app.get("/api/myth/{constellation}")
async def get_myth(constellation: str) -> dict:
    if constellation not in CONSTELLATION_NAMES:
        raise HTTPException(status_code=404, detail="unknown constellation")
    myth = pick_constellation_myth(constellation, MYTHS_DATA)
    image = None
    art_cfg = MYTH_ART_DATA.get(constellation)
    if art_cfg:
        image = get_constellation_art(constellation, art_cfg["category"])
    return {
        "constellation": constellation,
        "title": myth["title"] if myth else None,
        "text":  myth["text"] if myth else None,
        "image": image,
    }
```

- [ ] **Step 4: Run the full suite**

Run: `.venv/bin/python -m pytest -v`
Expected: PASS (all tests, including updated conftest consumers).

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/conftest.py tests/test_main.py
git commit -m "feat: legend + has_myth in /api/sky; add /api/myth endpoint"
```

---

## Task 8: Fonts + palette + base CSS

**Files:**
- Create: `app/static/fonts/` (woff2 files)
- Modify: `app/static/style.css`

**Interfaces:**
- Produces: CSS custom properties used by later steps —
  `--bg`, `--ink`, `--bone`, `--bone-dim`, `--gold`, `--oxblood`, font families
  `--font-title` (blackletter), `--font-body` (serif).

- [ ] **Step 1: Add the font files**

Download two SIL OFL fonts as woff2 into `app/static/fonts/`:
- Blackletter (titles): e.g. **UnifrakturCook** (`unifrakturcook-bold.woff2`).
- Baroque serif (body): e.g. **EB Garamond** (`ebgaramond-regular.woff2`,
  `ebgaramond-italic.woff2`).

Source: Google Fonts / fontsource (open licenses). If network is unavailable in
your environment, ask the operator to drop the woff2 files in. Verify presence:

```bash
ls app/static/fonts/*.woff2
```

- [ ] **Step 2: Declare fonts + palette at the top of `style.css`**

Prepend to `app/static/style.css`:

```css
@font-face {
  font-family: "Grimoire Title";
  src: url("/static/fonts/unifrakturcook-bold.woff2") format("woff2");
  font-weight: 700; font-display: swap;
}
@font-face {
  font-family: "Grimoire Body";
  src: url("/static/fonts/ebgaramond-regular.woff2") format("woff2");
  font-weight: 400; font-display: swap;
}
@font-face {
  font-family: "Grimoire Body";
  src: url("/static/fonts/ebgaramond-italic.woff2") format("woff2");
  font-weight: 400; font-style: italic; font-display: swap;
}

:root {
  --bg:       #08080a;
  --ink:      #14131a;
  --bone:     #e8e2d0;
  --bone-dim: #9b958a;
  --gold:     #d0a24a;
  --oxblood:  #7a2a26;
  --font-title: "Grimoire Title", "Times New Roman", serif;
  --font-body:  "Grimoire Body", Georgia, serif;
}
```

- [ ] **Step 3: Apply base typography**

In `style.css`, set body to `--font-body`/`--bone`/`--bg`, the wordmark, panel
headers (`.panel-hdr`), and any `*-title`/`-hdr` to `--font-title`. Keep the
runic headers; the blackletter face complements them. Reduce previously warm
parchment/gold backgrounds to near-monochrome using the new variables. Demote
gold to accents (the `% lit` value, the active highlight) and remove broad gold
usage.

- [ ] **Step 4: Verify the page still serves**

Run the app and load it (see Task 11 verification). Confirm fonts load from
`/static/fonts/` (no 404 in the network panel) and the page reads near-b/w.

- [ ] **Step 5: Commit**

```bash
git add app/static/fonts app/static/style.css
git commit -m "feat: bundle gothic+serif fonts and monochrome palette"
```

---

## Task 9: SVG moon + legend default + clickable cards + highlight (app.js)

**Files:**
- Modify: `app/static/index.html`, `app/static/app.js`

**Interfaces:**
- Consumes: `/api/sky` (`legend`, `constellations[].has_myth`, moon next-phase),
  `/api/myth/{name}` (`title`, `text`, `image`).

- [ ] **Step 1: Adjust `index.html`**

In `app/static/index.html`, leave the panel structure; ensure the legend body
container exists (`<div id="legend"></div>`) and add nothing else — the figure is
built in JS. (No change needed if `#legend` already present; confirm it is.)

- [ ] **Step 2: Replace `renderMoon` with an SVG moon**

In `app/static/app.js`, replace `renderMoon` with:

```javascript
  function moonSvg(illumPct, phaseName) {
    var C = 50, R = 46;
    var f = Math.max(0, Math.min(1, Number(illumPct) / 100));
    var n = String(phaseName || '').toLowerCase();
    var waxing = n.indexOf('waxing') >= 0 || n.indexOf('first') >= 0;
    var rx = R * (1 - 2 * f);                 // >0 crescent, <0 gibbous, 0 quarter
    var limbSweep = waxing ? 1 : 0;           // lit limb on lit side
    var termSweep = waxing ? (rx < 0 ? 1 : 0) // terminator bulge direction
                           : (rx < 0 ? 0 : 1);
    var top = C - R, bot = C + R;
    var d = 'M' + C + ',' + top +
            ' A' + R + ',' + R + ' 0 0,' + limbSweep + ' ' + C + ',' + bot +
            ' A' + Math.abs(rx).toFixed(2) + ',' + R + ' 0 0,' + termSweep + ' ' + C + ',' + top +
            ' Z';
    return '<svg class="moon-svg" viewBox="0 0 100 100" width="100" height="100" ' +
             'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">' +
             '<circle class="moon-shadow" cx="50" cy="50" r="46"/>' +
             '<path class="moon-lit" d="' + d + '"/>' +
             '<circle class="moon-limb" cx="50" cy="50" r="46"/>' +
           '</svg>';
  }

  function renderMoon(moon) {
    var rise    = moon.rise    || '—';
    var transit = moon.transit || '—';
    var set     = moon.set     || '—';

    var timesRow = moon.note
      ? '<div class="moon-note">' + esc(moon.note) + '</div>'
      : '<div class="moon-times">' +
          '<span><span class="dim">rise</span> <span class="val">' + esc(rise) + '</span></span>' +
          '<span><span class="dim">transit</span> <span class="val">' + esc(transit) + '</span></span>' +
          '<span><span class="dim">set</span> <span class="val">' + esc(set) + '</span></span>' +
        '</div>';

    var nextRow = '';
    if (moon.next_full_in_days != null || moon.next_new_in_days != null) {
      var parts = [];
      if (moon.next_full_in_days != null)
        parts.push('<span><span class="dim">full in</span> <span class="val">' +
                   esc(String(moon.next_full_in_days)) + 'd</span></span>');
      if (moon.next_new_in_days != null)
        parts.push('<span><span class="dim">new in</span> <span class="val">' +
                   esc(String(moon.next_new_in_days)) + 'd</span></span>');
      nextRow = '<div class="moon-next">' + parts.join('') + '</div>';
    }

    var el = document.getElementById('moon');
    el.innerHTML =
      '<div class="moon-phase">' +
        '<span class="moon-glyph"></span>' +
        '<span class="moon-name">' + esc(moon.phase_name) + '</span>' +
        '<span class="moon-illum">' + esc(String(moon.illumination_pct)) + '% lit</span>' +
      '</div>' + timesRow + nextRow;

    // inject the SVG moon via DOMParser (computed numbers only, no untrusted data)
    var glyph = el.querySelector('.moon-glyph');
    var doc = new DOMParser().parseFromString(
      moonSvg(moon.illumination_pct, moon.phase_name), 'image/svg+xml');
    glyph.appendChild(document.importNode(doc.documentElement, true));
  }
```

- [ ] **Step 3: Default legend renderer + myth swap**

Replace `renderMythology` (and its call in `render`) with a default-folklore
renderer plus a constellation-myth swapper:

```javascript
  function renderLegendDefault(legend) {
    document.getElementById('legend-hdr').textContent =
      'ᛚᛖᚷᛖᚾᛞ : ' + (legend.title || '');
    var el = document.getElementById('legend');
    el.innerHTML = '';
    if (legend.culture) {
      var cul = document.createElement('div');
      cul.className = 'legend-culture';
      cul.textContent = legend.culture;
      el.appendChild(cul);
    }
    var p = document.createElement('p');
    p.className = 'myth-text';
    p.textContent = legend.text || '';
    el.appendChild(p);
  }

  function renderMythFigure(image) {
    if (!image || !image.url) return null;
    var fig = document.createElement('figure');
    fig.className = 'myth-figure';
    var img = document.createElement('img');
    img.src = image.url;
    img.alt = image.title || '';
    img.loading = 'lazy';
    fig.appendChild(img);
    var cap = document.createElement('figcaption');
    var bits = [image.title, image.author, image.license].filter(Boolean).join(' · ');
    if (image.credit_url) {
      var a = document.createElement('a');
      a.href = image.credit_url; a.target = '_blank'; a.rel = 'noopener';
      a.textContent = bits || 'Wikimedia Commons';
      cap.appendChild(a);
    } else {
      cap.textContent = bits;
    }
    fig.appendChild(cap);
    return fig;
  }

  function showConstellationMyth(name) {
    fetch('/api/myth/' + encodeURIComponent(name))
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (m) {
        if (!m || !m.text) return;
        document.getElementById('legend-hdr').textContent = 'ᛚᛖᚷᛖᚾᛞ : ' + name;
        var el = document.getElementById('legend');
        el.innerHTML = '';
        if (m.title) {
          var h = document.createElement('div');
          h.className = 'myth-title';
          h.textContent = m.title;
          el.appendChild(h);
        }
        var p = document.createElement('p');
        p.className = 'myth-text';
        p.textContent = m.text;
        el.appendChild(p);
        var fig = renderMythFigure(m.image);
        if (fig) el.appendChild(fig);
      })
      .catch(function () { /* text stays; no user-facing error */ });
  }
```

- [ ] **Step 4: Cards + highlight + active toggle**

Replace `renderConstellations` and add highlight helpers + module state:

```javascript
  var activeConst = null;
  var defaultLegend = null;

  function clearHighlight() {
    var sky = document.getElementById('skymap');
    sky.classList.remove('has-hl');
    sky.querySelectorAll('.hl').forEach(function (n) { n.classList.remove('hl'); });
  }

  function highlight(name) {
    var sky = document.getElementById('skymap');
    var sel = '[data-constellation~="' + name.replace(/"/g, '\\"') + '"]';
    var nodes = sky.querySelectorAll(sel);
    if (!nodes.length) return;
    sky.classList.add('has-hl');
    nodes.forEach(function (n) { n.classList.add('hl'); });
  }

  function selectConstellation(name, card) {
    if (activeConst === name) {           // re-click → back to default
      deselect();
      return;
    }
    deselect();
    activeConst = name;
    card.classList.add('active');
    highlight(name);
    showConstellationMyth(name);
  }

  function deselect() {
    if (activeConst) {
      var prev = document.querySelector('.const-card.active');
      if (prev) prev.classList.remove('active');
    }
    activeConst = null;
    clearHighlight();
    if (defaultLegend) renderLegendDefault(defaultLegend);
  }

  function renderConstellations(list) {
    var container = document.getElementById('constellations');
    if (!list.length) {
      container.innerHTML = '<span class="const-empty">none visible</span>';
      return;
    }
    var sorted = list.slice().sort(function (a, b) {
      return (b.above_horizon ? 1 : 0) - (a.above_horizon ? 1 : 0);
    });
    container.innerHTML = '';
    sorted.forEach(function (c) {
      var card = document.createElement('div');
      card.className = 'const-card ' + (c.above_horizon ? 'above' : 'below') +
                       (c.has_myth ? '' : ' no-myth');
      card.innerHTML =
        '<span class="const-marker">' + (c.above_horizon ? '▲' : '▽') + '</span>' +
        '<span class="const-name"></span>' +
        '<span class="const-abbr"></span>';
      card.querySelector('.const-name').textContent = c.name;
      card.querySelector('.const-abbr').textContent = c.abbr;
      if (c.has_myth) {
        card.setAttribute('role', 'button');
        card.setAttribute('tabindex', '0');
        card.addEventListener('click', function () { selectConstellation(c.name, card); });
        card.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectConstellation(c.name, card); }
        });
      }
      container.appendChild(card);
    });
  }
```

Update `render` to store the default legend and use the new renderer:

```javascript
  function render(data, lat, lon) {
    setCoords(lat, lon);
    activeConst = null;
    defaultLegend = data.legend;
    renderMoon(data.moon);
    renderSkymap(data.skymap_svg);
    renderConstellations(data.constellations);
    renderLegendDefault(data.legend);
    document.getElementById('status').textContent = '';
    document.getElementById('panels').hidden = false;
  }
```

- [ ] **Step 5: Manual verification**

Run the app (Task 11). With a real or fallback location:
- Default legend shows a folklore title + culture + text; no image.
- Moon renders as an SVG with the correct lit fraction/side for the current
  phase.
- Clicking a clickable card highlights its lines/stars in gold, swaps the legend
  to that myth, and loads artwork (or stays text-only if offline).
- Re-clicking the active card restores the default legend and clears the
  highlight.
- `no-myth` cards don't respond to clicks.

- [ ] **Step 6: Commit**

```bash
git add app/static/index.html app/static/app.js
git commit -m "feat: SVG moon, folklore legend, clickable cards, sky highlight"
```

---

## Task 10: Visual styles — cards, figure, highlight, moon

**Files:**
- Modify: `app/static/style.css`

- [ ] **Step 1: Add component styles**

Append to `app/static/style.css` (use the Task 8 variables):

```css
/* moon */
.moon-svg { width: 96px; height: 96px; filter: drop-shadow(0 0 6px rgba(208,162,74,.25)); }
.moon-shadow { fill: #0d0c10; }
.moon-lit    { fill: var(--bone); }
.moon-limb   { fill: none; stroke: #2a2a2e; stroke-width: 1; }
.moon-illum  { color: var(--gold); }
.moon-next   { color: var(--bone-dim); }

/* constellation cards */
#constellations { display: flex; flex-wrap: wrap; gap: .4rem; }
.const-card {
  display: inline-flex; align-items: baseline; gap: .35rem;
  padding: .25rem .55rem; border-bottom: 1px solid transparent;
  color: var(--bone);
}
.const-card.below { color: var(--bone-dim); }
.const-card[role="button"] { cursor: pointer; }
.const-card[role="button"]:hover,
.const-card[role="button"]:focus-visible { border-bottom-color: var(--gold); outline: none; }
.const-card.active { color: var(--gold); border-bottom-color: var(--gold); }
.const-card.no-myth { opacity: .55; cursor: default; }
.const-abbr { font-size: .8em; color: var(--bone-dim); }

/* legend */
.legend-culture, .myth-title { font-family: var(--font-title); color: var(--gold); }
.myth-figure { margin: .8rem 0 0; }
.myth-figure img { width: 100%; height: auto; display: block; filter: grayscale(.15) contrast(1.05); }
.myth-figure figcaption { font-size: .75rem; color: var(--bone-dim); margin-top: .3rem; }
.myth-figure a { color: var(--bone-dim); }

/* sky highlight */
#skymap line.hl   { stroke: var(--gold); stroke-width: 1.6; stroke-opacity: 1;
                    filter: drop-shadow(0 0 3px var(--gold)); transition: all .2s ease; }
#skymap circle.hl { fill: var(--gold); filter: drop-shadow(0 0 3px var(--gold)); transition: all .2s ease; }
#skymap.has-hl line:not(.hl) { stroke-opacity: .25; }

@media (prefers-reduced-motion: reduce) {
  #skymap line.hl, #skymap circle.hl { transition: none; }
}
```

- [ ] **Step 2: Manual verification**

Reload the app: cards read as a wrapping row; active/dimmed/no-myth states are
distinct; the highlighted constellation glows gold while others dim; the legend
figure renders with a credit line; the moon SVG looks like an engraving.

- [ ] **Step 3: Commit**

```bash
git add app/static/style.css
git commit -m "feat: styles for cards, legend figure, sky highlight, moon"
```

---

## Task 11: Docs + full verification

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update `CLAUDE.md`**

- In the Architecture file list, add `app/mythart.py` (Wikimedia artwork client
  + cache) and the `data/dark_folklore.json`, `data/myths.json`,
  `data/myth_art.json` files; remove `data/mythology.json`.
- Update the request-flow paragraph to mention the new `/api/myth/{constellation}`
  endpoint and that `/api/sky` returns `legend` (not `mythology`).
- Update the **Test mocking** and **Mock binding (T6.1)** notes: patched names
  are now `app.main.pick_default_folklore` and `app.main.pick_constellation_myth`
  (still `app.main.*` bindings via `from .astronomy import …`); the `/api/sky`
  field is `legend`.

- [ ] **Step 2: Run the full test suite**

Run: `.venv/bin/python -m pytest -v`
Expected: PASS (all tests).

- [ ] **Step 3: Manual end-to-end run**

```bash
SKYFIELD_DATA=/path/to/local/skyfield-data \
  .venv/bin/python -m uvicorn app.main:app --port 7432
```

Open `http://localhost:7432`, allow geolocation (or rely on `LAT`/`LON`
fallback), and walk the full manual checklist from the spec's "Testing &
verification" section.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update architecture and mock-binding notes"
```

---

## Self-Review notes

- **Spec coverage:** next-phase (T3), default folklore (T1/T2/T7), constellation
  myths + cast/role (T1/T2), daily-fixed selection (T2), artwork live+cached
  +categories (T6/T7), constellation-myths-only image scope (T7/T9), sky
  highlight (T4/T5/T9/T10), `has_myth` clickability (T7/T9), gothic type (T8),
  monochrome palette (T5/T8/T10), SVG moon (T9/T10), tests + docs (every task,
  T11). All spec sections map to a task.
- **External-network isolation:** only T6/`mythart.py` touches the network, only
  via the lazy `/api/myth` path; `/api/sky` stays offline-capable.
- **Mock-binding rule:** `main.py` keeps `from .astronomy import …`; conftest
  patches `app.main.*` (T7).
