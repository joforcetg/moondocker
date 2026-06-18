# moondocker — legends, constellation myths & sky highlight — design

**Date:** 2026-06-18
**Status:** approved (design), pending implementation plan
**Branch:** `frontend-refresh`

## Summary

Content + interaction enrichment of the moondocker frontend, with supporting
backend work. Five threads:

1. **Next moon-phase dates** — show "Full moon in N days" etc.
2. **Default legend = dark world folklore** — the legend panel's default content
   becomes a curated pool of dark-toned myth/folklore from any culture (night,
   witches, monsters), unrelated to the constellations.
3. **Clickable constellation cards → constellation myths** — clicking a
   constellation surfaces a myth that features that constellation's character.
4. **Classical artwork** — a constellation myth is accompanied by a real
   classical-period artwork fetched live from Wikimedia Commons (cached).
5. **Sky highlight** — clicking a constellation card lights up that
   constellation's stick figure in the night-sky SVG.
6. **Visual refresh** — gothic/baroque type, a near monochrome (black & white)
   palette with the warm accents kept sparse, and a themed b/w moon illustration
   replacing the emoji phase glyph.

This keeps the Candlelit Grimoire mood, vanilla JS, no build step. It changes
the `/api/sky` contract (one field renamed, several additive fields) and adds
one new endpoint and one new external-network module.

## Goals

- Default legend is free-standing dark folklore, daily-fixed, any culture.
- Constellation cards are clickable; a click shows a daily-fixed myth featuring
  that constellation, its classical artwork, and highlights it in the sky.
- Moon panel shows next new/full dates.
- The live external fetch is isolated, cached, and degrades gracefully to text
  when offline or unmatched — the core sky view stays self-contained.
- Gothic/baroque typography, a near-monochrome palette, and a themed moon
  illustration, self-hosted (no CDN, no build step).

## Non-goals (YAGNI)

- No JS framework, bundler, or build step.
- No per-user state, accounts, or persistence beyond an in-memory cache.
- No backend almanac features beyond next new/full moon.
- No image generation — myth artwork is real, sourced from Wikimedia Commons;
  the moon illustration is drawn programmatically as SVG (not an asset).
- No web-font CDN — fonts are bundled woff2 files served from `/static`.
- No new colors beyond the existing Candlelit Grimoire palette (candle-gold is
  reused for the highlight).

## Decisions (from brainstorming)

- **Default legend:** dark world folklore, any culture, **daily-fixed**.
- **Constellation → myth mapping:** a myth carries an ordered `cast` of up to 3
  constellations (lead / second / third). A constellation's eligible pool is
  every myth where it appears in that top-3.
- **Click selection:** **daily-fixed** — the myth shown for a constellation is
  deterministic by date; repeated clicks don't change it.
- **Artwork scope:** constellation myths only. Default folklore is text-only.
- **Artwork delivery:** live from Wikimedia Commons, **cached + refreshed
  weekly** (7-day TTL), lazy per-constellation.
- **Artwork relevance:** **curated Commons categories** — one hand-picked
  category per constellation; server pulls a random category member.
- **Sky highlight:** clicking a card highlights that constellation's stick
  figure (lines + member stars) in the SVG.
- **Typography:** gothic **blackletter for titles** (wordmark, panel headers,
  legend/myth titles); **baroque old-style serif for body** (prose, labels).
- **Palette:** keep the Candlelit Grimoire hues but push **toward black &
  white** — ink-black background, bone/off-white text; candle-gold and oxblood
  demoted to sparse accents (highlight, key values) only.
- **Moon illustration:** replace the emoji phase glyph with a **themed b/w SVG
  moon** (engraving look), drawn client-side from illumination + waxing/waning.

## Visual refresh

### Typography

- **Blackletter (titles):** an open-licensed gothic display face (e.g.
  UnifrakturCook or Pirata One, SIL OFL) for the `moondocker` wordmark, the runic
  panel headers' companion text, and legend/myth titles.
- **Baroque serif (body):** an old-style serif (e.g. EB Garamond or Cormorant,
  SIL OFL) for myth/folklore prose, field labels, and values.
- **Self-hosted:** woff2 files in `app/static/fonts/`, declared via `@font-face`
  in `style.css`. No CDN, no build step. Monospace is dropped from the UI chrome;
  the sky-map cardinal labels may stay a simple serif/mono for legibility.
- Runic panel headers (user loves them) are kept.

### Palette (near-monochrome)

- Background: ink-black (existing warm ink-black, slightly desaturated).
- Text: bone / off-white at a few brightness steps for hierarchy (replacing the
  saturated aged-parchment tone with a more neutral bone).
- **Accents, used sparingly:** candle-gold for the moon illustration, the active
  sky highlight, and a few key values (e.g. `% lit`); oxblood for an occasional
  emphasis. Everything else is grayscale.
- The sky-map SVG default colors shift toward monochrome too: bone stars on
  near-black, neutral-gray stick-figure lines, gray cardinals — so the
  candle-gold `.hl` highlight reads strongly against a b/w field.

### Moon illustration

- A client-side SVG disk with a shaded terminator, rendered from
  `moon.illumination_pct` and the waxing/waning sense derived from
  `moon.phase_name` ("Waxing"/"Waning"/"New"/"Full"). Engraving/woodcut b/w
  styling: bone-lit limb, deep-shadow dark side, a fine outline; candle-gold used
  only as a faint glow, in keeping with the sparse-accent rule.
- `moon.phase_glyph` (emoji) stays in the `/api/sky` response for compatibility
  but is no longer displayed.

## Data model

Three new data files; the existing `data/mythology.json` is retired (its content
is superseded by `myths.json` + `dark_folklore.json`).

### `data/dark_folklore.json` (new)

Default legend pool. ~20–25 entries, dark/night/witch/monster tone, any culture,
**not** constellation-tied.

```json
[
  {
    "id": "wendigo",
    "title": "The Wendigo",
    "culture": "Algonquian",
    "text": "A gaunt spirit of winter hunger that walks the frozen woods..."
  }
]
```

### `data/myths.json` (new)

Constellation myths with role-ordered cast. ~25–40 entries covering the 20
constellations that have `myth_art` categories.

```json
[
  {
    "id": "orion-scorpius",
    "title": "Orion and the Scorpion",
    "text": "The hunter Orion boasted he could kill any beast...",
    "cast": ["Orion", "Scorpius"]
  }
]
```

- `cast` is 1–3 constellation `name`s in role order (index 0 = lead, 1 = second,
  2 = third). Names must match `data/constellations.json` `name` values exactly.
- A constellation's eligible pool = every myth whose `cast` contains that name.

### `data/myth_art.json` (new)

```json
{ "Orion": { "category": "Category:Orion in art" } }
```

20 entries, one curated Wikimedia Commons category per constellation. Keyed by
constellation `name`.

### Content authoring

The folklore entries, myths (with cast tagging), and category mappings are
authored as part of implementation. They are plain data files the user can edit
later. Myth and folklore text is original/paraphrased prose, not copied verbatim
from copyrighted sources.

## Backend

### `app/astronomy.py`

**`get_moon_data` — next-phase fields (additive).**
Using `skyfield.almanac.moon_phases(eph)` + `find_discrete` over `t … t+40d`,
find the next New (event `0`) and next Full (event `2`) after `t`. Add to the
returned dict:

- `next_new_date`, `next_new_in_days`
- `next_full_date`, `next_full_in_days`

ISO date strings + integer day counts. Wrapped in `try/except` like the existing
rise/set lookups; on failure the four fields are `None`.

**Replace `pick_mythology` with two functions:**

- `pick_default_folklore(folklore, date_str=None) -> dict` — daily-fixed pick
  from `dark_folklore.json`. Returns `{id, title, culture, text}`. Reuses the
  existing md5(date)-seed approach.
- `pick_constellation_myth(name, myths, date_str=None) -> dict | None` —
  eligible pool = myths where `name in cast`, ordered by role (myths where
  `name` is the lead first, then second, then third); within that ordering pick
  one daily-fixed by date seed. Returns `{constellation, title, text}` or `None`
  if the constellation has no myths.

### `app/mythart.py` (new)

Live Wikimedia Commons client + cache.

- `get_constellation_art(name, categories) -> dict | None` — returns
  `{url, title, author, license, credit_url}` or `None`.
- **Lookup:** `list=categorymembers&cmtype=file&cmlimit=100` for the curated
  category → choose a random file → `prop=imageinfo&iiprop=url|extmetadata` for
  the image URL plus `Artist` / `LicenseShortName` / `Credit` extmetadata.
- **Transport:** stdlib `urllib.request` (no new dependency), ~5s timeout,
  descriptive `User-Agent` (e.g. `moondocker/1.0 (+https://github.com/joforcetg/moondocker)`)
  as Wikimedia requires.
- **Cache:** module-level `dict` `{name: (fetched_at_monotonic_or_epoch, payload)}`,
  7-day TTL, lazy. Lost on process restart (refetched on demand). No disk.
- **Failure handling:** any network/parse error or empty category → returns
  `None`; never raises to the caller.

### `app/main.py`

**`GET /api/sky` (modified).**
- Moon object gains the four next-phase fields.
- The `mythology` field is **renamed to `legend`**, now carrying the daily-fixed
  default folklore: `{id, title, culture, text}`.
- Each entry in `constellations[]` gains `has_myth: bool` (true when the
  constellation has at least one eligible myth) so the frontend knows which
  cards are clickable.

**`GET /api/myth/{constellation}` (new).**
- Validates `{constellation}` against the known constellation `name` set
  (from `constellations.json`); unknown → `404`. This prevents arbitrary
  category / URL fetches.
- Returns `{constellation, title, text, image}` where `text`/`title` come from
  `pick_constellation_myth` and `image` is the cached Wikimedia payload or
  `null`. If the constellation has no myth, returns `text: null` (cards for such
  constellations are non-clickable, so this is a defensive case).

## Sky-map tagging

### `app/astronomy.py::get_skymap_stars`

Each `const_lines` entry gains the owning constellation:
`{hip_a, hip_b, constellation}` (additive — existing consumers ignore the extra
key).

### `app/skymap.py::generate_skymap`

- Stamp each stick-figure `<line>` with `data-constellation="<name>"`.
- Derive figure-star membership from the lines; stamp those `<circle>`s with a
  space-joined `data-constellation` (a star may belong to several
  constellations) plus a `figstar` class. Background stars and cardinals stay
  untagged.
- Names come from `constellations.json` (trusted, server-generated). Attribute
  values are emitted via the same formatting as other attributes; names are
  known-safe ASCII/Latin (e.g. `Boötes`).
- Matched in the frontend via the whitespace-token selector
  `[data-constellation~="Name"]`.
- **Monochrome recolor:** default star/line/cardinal colors shift to a
  near-b/w scheme (bone stars, neutral-gray lines, gray cardinals) so the
  candle-gold `.hl` highlight stands out. Color values are still set in
  `skymap.py`; the highlight color lives in `style.css` via the `.hl` class.

## Frontend

### `app/static/index.html`

- Legend panel markup gains a container for an optional `<figure>` (image +
  credit `<figcaption>`).
- Constellations container holds cards instead of chips.

### `app/static/app.js`

- **`render`:** legend shows `data.legend` (default folklore: title · culture ·
  text), no image, on load.
- **`renderMoon` → SVG moon:** instead of printing `moon.phase_glyph`, build a
  themed b/w SVG moon disk with a shaded terminator from `moon.illumination_pct`
  and the waxing/waning sense parsed from `moon.phase_name`. Engraving styling
  per the Visual refresh section. Drawn with the same safe DOM construction
  (no raw-string `innerHTML` of untrusted data).
- **`renderConstellations` → cards:** name, abbr, `▲/▽` marker, above-first sort
  (kept). A card is clickable only when its constellation entry has
  `has_myth: true`; non-clickable cards are dimmed. Cards are keyboard
  accessible (`role="button"`, `tabindex="0"`, Enter/Space).
- **Card click** does three things:
  1. `fetch('/api/myth/' + encodeURIComponent(name))` → swap legend to
     `{title, text}`; if `image` present, append a `<figure>` with `<img>` and a
     credit `<figcaption>` (title · author · license, linked to `credit_url`).
     All strings `esc()`'d; the image is loaded by the browser from
     `upload.wikimedia.org`. Fetch failure / `image: null` → text-only, no error.
  2. Highlight: `#skymap` SVG → `querySelectorAll('[data-constellation~="Name"]')`
     → add `.hl`; add `.has-hl` to the skymap container so non-highlighted lines
     dim.
  3. Mark the card active.
- **Re-click the active card** → clear highlight, restore default folklore
  legend, remove active state.
- SVG injection stays `DOMParser` + `importNode` (unchanged); the inline SVG
  nodes are queryable for highlighting.

### `app/static/fonts/` (new)

Bundled woff2 files: one blackletter display face (titles) and one baroque
old-style serif (body), both SIL OFL. Declared via `@font-face` in `style.css`.

### `app/static/style.css`

- **`@font-face`** for the bundled blackletter + serif; apply blackletter to
  titles (wordmark, panel headers, legend/myth titles) and serif to body.
- **Palette shift:** move CSS custom properties toward near-monochrome
  (ink-black bg, bone text at a few steps); candle-gold / oxblood reduced to
  sparse-accent variables (highlight, key values).
- **Typography pass:** type scale, spacing rhythm, hierarchy across panels in the
  new palette.
- **Card styles:** active / clickable / dimmed states.
- **Figure / credit styles** for the legend artwork.
- **Moon SVG styles** for the engraving look (limb, terminator, faint glow).
- **Highlight styles:** `#skymap line.hl` candle-gold + glow; `#skymap
  circle.hl` brighter/larger; `#skymap.has-hl line:not(.hl)` dimmed. All
  transitions gated behind `prefers-reduced-motion: reduce`.

## Data flow

- **Load:** `init()` → geolocation/fallback → `GET /api/sky` → `render()`:
  moon (with next-phase), sky SVG (tagged), cards (with `has_myth`), default
  folklore legend.
- **Card click:** `GET /api/myth/{name}` → legend text + artwork + sky highlight.
  Independent of `/api/sky`; does not re-fetch sky data.

## Error & edge handling

- **Geolocation denied / no fallback / server error:** unchanged behavior.
- **Empty constellations:** `none visible` (kept).
- **No myth for a constellation:** card non-clickable (`has_myth: false`).
- **Wikimedia unavailable / offline / no category match:** `image: null`,
  legend stays text-only, no user-facing error.
- **Polar moon `note`:** still replaces the rise/set row (kept).

## Testing & verification

- **`tests/conftest.py`:** the `app.main.pick_mythology` patch is replaced by
  patches for the new names actually imported into `app.main`
  (`pick_default_folklore`, `pick_constellation_myth`) and the `/api/sky`
  response key `mythology` → `legend` is reflected in fixtures.
- **`tests/test_astronomy.py`:** tests for `pick_default_folklore` (daily
  determinism), `pick_constellation_myth` (eligible-pool filtering by cast,
  role ordering, daily determinism, `None` when no myth), and the next-phase
  fields (mocked skyfield).
- **`tests/test_skymap.py`:** assert stick-figure lines and figure stars carry
  `data-constellation`; background elements do not.
- **`app/mythart.py`:** new tests with `urllib` mocked — successful parse,
  empty category → `None`, network error → `None`, cache hit avoids refetch,
  TTL expiry triggers refetch.
- **`app/main.py`:** test `GET /api/myth/{constellation}` for a valid name
  (mythart mocked), an unknown name → `404`, and a no-myth constellation.
- No JS test harness exists; none added (YAGNI). Manual checklist:
  - Default legend shows dark folklore; no image.
  - Clicking a clickable card swaps legend text, loads artwork (or text-only if
    unavailable), and highlights the constellation in the sky.
  - Re-clicking the active card restores the default legend and clears the
    highlight.
  - Non-`has_myth` cards are visibly non-clickable.
  - Moon panel shows next new/full dates.
  - Moon SVG matches the phase (correct lit fraction + waxing/waning side) at
    new, crescent, quarter, gibbous, and full.
  - Blackletter renders on titles, serif on body; fonts load from `/static`
    (no network/CDN).
  - Palette reads near-b/w with sparse gold/oxblood accents; sky-map highlight
    pops in candle-gold.
  - `prefers-reduced-motion` disables highlight/fade transitions.
- `.venv/bin/python -m pytest -v` green.

## Docs

- Update the CLAUDE.md "Mock binding (T6.1)" note: the patched names are now
  `pick_default_folklore` / `pick_constellation_myth` (still `app.main.*`
  bindings via `from .astronomy import …`), and the `/api/sky` mythology field
  is renamed to `legend`.
- Note the new `app/mythart.py` external-network dependency and the new
  `/api/myth/{constellation}` endpoint in the Architecture section.

## Risk

Medium. Backend `/api/sky` contract change (one rename + additive fields), a new
endpoint, and a new external-network module. Mitigated: the live fetch is
isolated behind one lazy, cached endpoint that returns `null` on any failure, so
the core sky view remains fully self-contained and offline-capable. No Docker or
astronomy-core math changes beyond the additive almanac lookup and line tagging.
