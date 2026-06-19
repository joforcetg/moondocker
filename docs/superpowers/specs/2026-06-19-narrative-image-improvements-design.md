# Narrative & Image Improvements

**Date:** 2026-06-19
**Status:** Approved

## Goal

Richer content and more reliable artwork for moondocker's legend and constellation panels.

## Scope

Three files change:

| File | What changes |
|---|---|
| `data/dark_folklore.json` | Expand pool, richer horror prose |
| `data/myths.json` | Richer myth texts, more cultural variety |
| `data/myth_art.json` | Add alternate categories and search terms |
| `app/mythart.py` | Multi-strategy Wikimedia lookup |

No schema changes to the API. No new dependencies.

---

## 1. `dark_folklore.json`

### Current state
20 entries, ~150–330 chars each (1–2 sentences).

### Target state
~50 entries. Each entry 3–5 sentences of atmospheric horror prose. First-person dread where the tradition allows it.

### Schema (unchanged)
```json
{
  "id": "slug",
  "title": "Name",
  "culture": "Culture name",
  "text": "3–5 sentences of horror prose."
}
```

### Cultural spread to add
Existing entries cover: Algonquian, Mexican, Romanian, Slavic, Japanese (×2), Breton, Filipino, Orcadian, Buddhist, English, Aztec, German, Irish, East Anglian, Norse, Malay, Siberian Yakut, Trinidad/Tobago.

Add coverage from: West African (Yoruba, Akan), Andean (Quechua), Polynesian (Māori, Hawaiian), Central Asian (Kazakh, Mongolian), Southeast Asian (Thai, Indonesian), Aboriginal Australian, Middle Eastern (Arabian, Persian), pre-Columbian (Maya, Inca), Eastern European (Hungarian, Bulgarian), South Asian (Indian, Sri Lankan).

### Tone
Horror-first. Not neutral mythology — these should feel like warnings. Dark night sky context (nocturnal, cold, sky-watching).

---

## 2. `myths.json`

### Current state
31 entries covering all 20 constellations. Texts 150–230 chars (1–2 sentences). Almost entirely Greek/Roman tradition.

### Target state
Expand existing myth texts to 4–6 sentences each (paragraph). Neutral mythological register: explain the story, name the characters, say why they were placed in the sky. Add 15–20 new myth entries from non-Greek traditions.

### Schema (unchanged)
```json
{
  "id": "slug",
  "title": "Title",
  "text": "4–6 sentence paragraph.",
  "cast": ["ConstellationName", ...]
}
```

### Cast constraint
`cast` entries must use the exact constellation names from `constellations.json`:
Andromeda, Aquarius, Aquila, Auriga, Boötes, Canis Major, Cassiopeia, Cygnus, Gemini, Hercules, Leo, Lyra, Orion, Perseus, Sagittarius, Scorpius, Taurus, Ursa Major, Ursa Minor, Virgo.

### Non-Greek traditions to add
- **Arabic**: star-lore connected to these constellation figures (Orion as al-Jabbar, Gemini as the twins al-Tawʾamān)
- **Mesopotamian/Babylonian**: original myths these Greek myths derived from (Scorpius as Girtablullu, Taurus as the Bull of Heaven)
- **Chinese**: lunar mansion figures for Orion (Shen 參), Scorpius (Xin 心), Virgo (Jiao 角)
- **Lakota / Plains Indigenous**: Star Boy, Fallen Star stories tied to Orion, Ursa Major, Pleiades (Taurus)
- **Aztec**: Mamalhuaztli (Orion's belt as fire drill), Citlaltlachtli (Scorpius as ball-game court)

### Tone
Neutral mythological. Not horror. Explains the myth, names the characters, gives the celestial reason.

---

## 3. `myth_art.json`

### Current state
20 entries, one category string per constellation.

### Target state
Each entry gains `alt_categories` (array, ordered) and `search_terms` (array). Original `category` field kept.

### New schema
```json
{
  "Orion": {
    "category": "Category:Orion in art",
    "alt_categories": [
      "Category:Orion (mythology)",
      "Category:Uranometria"
    ],
    "search_terms": [
      "Orion constellation Bayer Uranometria",
      "Orion hunter mythology engraving"
    ]
  }
}
```

### Historical atlas categories (always useful fallbacks)
- `Category:Uranometria` — Bayer 1603, detailed engravings of all 48 Ptolemaic constellations
- `Category:Firmamentum Sobiescianum` — Hevelius 1690
- `Category:Atlas Coelestis` — Flamsteed 1729
- `Category:Urania's Mirror` — Sidney Hall 1824, coloured cards

These are public domain, always on Wikimedia, visually perfect for the grimoire aesthetic.

---

## 4. `app/mythart.py`

### Current flow
1. Try `category` → `_category_titles`
2. If empty, `_search_titles(name)`

### New flow (ordered, stops at first hit)
1. `category` field → `_category_titles`
2. Each entry in `alt_categories` → `_category_titles`
3. Each entry in `search_terms` → `_search_titles` (exact query)
4. Generic fallback: `_search_titles(f"{name} constellation mythology art")`
5. Atlas fallback: `_search_titles(f"{name} Uranometria")`, then Flamsteed, then Hevelius

### API contract (unchanged)
```python
def get_constellation_art(name: str, category: str) -> dict | None:
```
Signature stays the same. Internally loads `myth_art.json` for `alt_categories` and `search_terms`. Cache logic unchanged.

### Implementation note
Load `myth_art.json` once at module level (like `MYTH_ART: dict = json.loads(...)`). `_fetch_art` receives the full entry dict instead of just `category` string. Update `_fetch_art(entry, name)` signature internally; external API unchanged.

---

## Testing

Existing tests patch `app.main.get_constellation_art` — no changes needed to test patches.

New unit tests in `tests/test_mythart.py`:
- `test_falls_back_to_alt_category` — first category empty, second returns result
- `test_falls_back_to_search_terms` — all categories empty, search_terms hit
- `test_falls_back_to_atlas_search` — all empty, atlas search hits
- `test_all_strategies_exhausted_returns_none`

---

## 5. `app/skymap.py` — Aesthetic alignment

### Problem
Skymap SVG uses warm sepia tones, clashing with the cold horror CSS palette.

### Changes (color values only, no logic)

| Element | Current | New |
|---|---|---|
| Constellation lines stroke | `#6b6256` | `#4a4a52` |
| Figure stars fill | `#ece7da` | `#cacace` |
| Background stars fill | `#cfc8b8` | `#9a9aa8` |
| Background stars fill-opacity | `0.85` | `0.6` |
| Cardinal text fill | `#8a8276` | `#7e7e85` |
| Boundary circle stroke | `#2a2a2e` | unchanged |
| Background fill | `#08080a` | unchanged |

No projection, logic, or API changes.

---

## 6. `app/static/app.js` — Minor polish

### Constellation card markers
Change `▲` / `▽` to `·` / `∘` — quieter, less chunky, fits grimoire aesthetic.

### Everything else
Moon SVG rendering, fetch logic, highlight system, layout structure — all sound, no changes.

---

---

## 7. `app/static/index.html` — Wordmark rename

Change `moondocker` → `Moonseek` in:
- `<title>Moonseek</title>`
- `<span class="wordmark">Moonseek</span>`

No other files reference the display name.

---

## Out of scope

- No API endpoint changes
- No new runtime dependencies
- No changes to `astronomy.py` or `main.py`
