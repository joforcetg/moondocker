# moondocker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single Docker container that serves a web UI displaying tonight's moon phase, an SVG night sky map, visible constellations, and a daily mythology trivia blurb — all computed server-side from the user's geographic coordinates.

**Architecture:** FastAPI + Uvicorn serves both a JSON astronomy API (`GET /api/sky?lat=X&lon=Y`) and static HTML/CSS/JS. All astronomy is computed in Python using `skyfield` with data files baked into the image at build time. The sky map is an SVG generated on the server and embedded in the API response. Mythology trivia rotates daily via a deterministic date-based seed.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, skyfield 1.49, numpy — base image `python:3.12-slim`, port 7432, no external API calls at runtime.

---

## File Map

```
moondocker/
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── requirements.txt           # prod deps
├── requirements-dev.txt       # adds pytest + httpx
├── data/
│   ├── constellations.json    # 20 constellations: names, HIP IDs, stick-figure lines
│   └── mythology.json         # 2 trivia entries per constellation
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI app: routes, static files, LAT/LON injection
│   ├── astronomy.py           # skyfield computations + pure helpers
│   ├── skymap.py              # SVG generator (pure math, no skyfield)
│   └── static/
│       ├── index.html         # page shell with ASCII/runic chrome
│       ├── style.css          # monospace dark theme
│       └── app.js             # geolocation → API fetch → DOM render
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_skymap.py
    ├── test_astronomy.py
    └── test_main.py
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`
- Create: `app/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p app/static data tests
touch app/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write `requirements.txt`**

```
fastapi>=0.111
uvicorn[standard]>=0.29
skyfield>=1.49
numpy>=1.26
```

- [ ] **Step 3: Write `requirements-dev.txt`**

```
-r requirements.txt
pytest>=8.0
httpx>=0.27
```

- [ ] **Step 4: Write `Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Pre-download skyfield data at build time so the container runs offline
RUN python - <<'EOF'
from skyfield.api import Loader
from skyfield.data import hipparcos
load = Loader('/skyfield-data')
load('de421.bsp')
with load.open('hip_main.dat') as f:
    hipparcos.load_dataframe(f)
EOF
COPY data/ ./data/
COPY app/ ./app/
ENV LAT="" LON="" PORT=7432 SKYFIELD_DATA=/skyfield-data
EXPOSE 7432
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```

- [ ] **Step 5: Write `docker-compose.yml`**

```yaml
services:
  moondocker:
    build: .
    ports:
      - "7432:7432"
    environment:
      LAT: ""   # fallback latitude; leave blank to use browser geolocation
      LON: ""   # fallback longitude
```

- [ ] **Step 6: Write `.dockerignore`**

```
.git
tests/
docs/
*.md
__pycache__
*.pyc
.pytest_cache
```

- [ ] **Step 7: Commit**

```bash
git add requirements.txt requirements-dev.txt Dockerfile docker-compose.yml .dockerignore app/__init__.py tests/__init__.py
git commit -m "feat: project scaffolding — Dockerfile, requirements, directory structure"
```

---

## Task 2: Data Files

**Files:**
- Create: `data/constellations.json`
- Create: `data/mythology.json`

- [ ] **Step 1: Write `data/constellations.json`**

Each entry has `name`, `abbr`, `hip_ids` (used to compute visibility — average altitude of these Hipparcos star IDs), and `lines` (HIP ID pairs to draw as stick-figure line segments).

```json
[
  {
    "name": "Orion", "abbr": "Ori",
    "hip_ids": [27989, 24436, 25336, 23419, 26311, 26727, 27366],
    "lines": [[27989,25336],[27989,26727],[25336,23419],[23419,26311],[26311,26727],[24436,26727],[24436,27366]]
  },
  {
    "name": "Ursa Major", "abbr": "UMa",
    "hip_ids": [54061, 53910, 58001, 59774, 62956, 65378, 67301],
    "lines": [[54061,53910],[53910,58001],[58001,59774],[59774,62956],[62956,65378],[65378,67301]]
  },
  {
    "name": "Cassiopeia", "abbr": "Cas",
    "hip_ids": [746, 3179, 4427, 6686, 8886],
    "lines": [[746,3179],[3179,4427],[4427,6686],[6686,8886]]
  },
  {
    "name": "Leo", "abbr": "Leo",
    "hip_ids": [49669, 50583, 54879, 57632, 47908],
    "lines": [[49669,50583],[50583,54879],[54879,57632],[50583,47908]]
  },
  {
    "name": "Scorpius", "abbr": "Sco",
    "hip_ids": [78401, 79417, 80763, 85696, 85927],
    "lines": [[78401,79417],[79417,80763],[80763,85696],[85696,85927]]
  },
  {
    "name": "Cygnus", "abbr": "Cyg",
    "hip_ids": [102098, 100453, 95947, 98110, 97165],
    "lines": [[102098,100453],[100453,95947],[100453,98110],[100453,97165]]
  },
  {
    "name": "Lyra", "abbr": "Lyr",
    "hip_ids": [91262, 92420, 93194],
    "lines": [[91262,92420],[92420,93194],[91262,93194]]
  },
  {
    "name": "Aquila", "abbr": "Aql",
    "hip_ids": [97649, 97278, 97804],
    "lines": [[97278,97649],[97649,97804]]
  },
  {
    "name": "Gemini", "abbr": "Gem",
    "hip_ids": [36850, 37826, 32246, 34693],
    "lines": [[36850,32246],[37826,34693],[36850,37826],[32246,34693]]
  },
  {
    "name": "Taurus", "abbr": "Tau",
    "hip_ids": [21421, 25428, 17702],
    "lines": [[21421,25428],[21421,17702]]
  },
  {
    "name": "Virgo", "abbr": "Vir",
    "hip_ids": [65474, 61941, 63608],
    "lines": [[65474,61941],[61941,63608]]
  },
  {
    "name": "Boötes", "abbr": "Boo",
    "hip_ids": [69673, 72105, 71075, 73555],
    "lines": [[69673,72105],[69673,71075],[71075,73555]]
  },
  {
    "name": "Perseus", "abbr": "Per",
    "hip_ids": [15863, 14576, 18532],
    "lines": [[15863,14576],[15863,18532]]
  },
  {
    "name": "Auriga", "abbr": "Aur",
    "hip_ids": [24608, 28360, 23767],
    "lines": [[24608,28360],[24608,23767]]
  },
  {
    "name": "Canis Major", "abbr": "CMa",
    "hip_ids": [32349, 33579, 34444, 30324],
    "lines": [[30324,32349],[32349,33579],[33579,34444]]
  },
  {
    "name": "Aquarius", "abbr": "Aqr",
    "hip_ids": [106278, 109074, 102618],
    "lines": [[109074,106278],[106278,102618]]
  },
  {
    "name": "Sagittarius", "abbr": "Sgr",
    "hip_ids": [90185, 92855, 89931],
    "lines": [[90185,89931],[89931,92855]]
  },
  {
    "name": "Hercules", "abbr": "Her",
    "hip_ids": [80816, 81693, 84379],
    "lines": [[80816,81693],[81693,84379]]
  },
  {
    "name": "Ursa Minor", "abbr": "UMi",
    "hip_ids": [11767, 85822, 82080, 77055, 79822, 72607, 75097],
    "lines": [[11767,85822],[85822,82080],[82080,77055],[77055,79822],[79822,72607],[72607,75097]]
  },
  {
    "name": "Andromeda", "abbr": "And",
    "hip_ids": [677, 5447, 9640],
    "lines": [[677,5447],[5447,9640]]
  }
]
```

- [ ] **Step 2: Write `data/mythology.json`**

```json
{
  "Orion": [
    "In Greek mythology, Orion was a giant hunter, son of Poseidon. After his death — at the hands of Artemis or a scorpion, depending on the account — Zeus placed him among the stars. He eternally pursues the Pleiades across the sky.",
    "The ancient Egyptians identified Orion's belt with Osiris, lord of the dead. They oriented the Great Pyramid's southern shafts toward Orion's belt stars, aligning the pharaoh's soul with the celestial realm of Osiris."
  ],
  "Ursa Major": [
    "In Greek myth, Zeus transformed the nymph Callisto into a bear to protect her from Hera's jealousy. Her son Arcas nearly killed her unknowingly while hunting, so Zeus placed them both in the heavens — Callisto as Ursa Major, Arcas as Boötes or Ursa Minor.",
    "Native American traditions across tribes see the Big Dipper's bowl as a cooking pot or spiritual vessel. The Algonquin called the four bowl stars 'the Great Bear' and the three handle stars its hunting cubs — independently mirroring the Greek name."
  ],
  "Cassiopeia": [
    "Cassiopeia was a vain Ethiopian queen who boasted her beauty exceeded that of the sea nymphs. Poseidon punished her kingdom with a sea monster, and her daughter Andromeda was chained to a rock as sacrifice before Perseus intervened.",
    "Tycho Brahe observed the famous supernova of 1572 — 'Tycho's Star' — blazing within Cassiopeia's borders. It briefly outshone Venus, challenging the Aristotelian doctrine that the heavens were perfect and unchanging."
  ],
  "Leo": [
    "The Nemean Lion was the first of Heracles' twelve labors. Invulnerable to mortal weapons, it was strangled bare-handed. Zeus commemorated the feat by placing the lion among the stars — its bright heart marked by Regulus, meaning 'the little king.'",
    "Regulus lies almost exactly on the ecliptic — the Sun's path. Ancient astrologers named it one of the four Royal Stars: a guardian of heaven, associated with the archangel Raphael, and considered a watcher of the north sky."
  ],
  "Scorpius": [
    "Orion the hunter boasted he would kill every beast on earth. Gaia, protector of wildlife, sent a scorpion to stop him. Zeus placed them at opposite ends of the sky so they would never meet — Orion sets in the west as Scorpius rises in the east.",
    "Antares literally means 'rival of Ares' (Mars) in Greek — its color so closely mirrors the red planet that ancient stargazers confused them. Antares is a supergiant so vast that if placed at our Sun's position, it would engulf all planets out to Mars."
  ],
  "Cygnus": [
    "Cygnus represents the swan form Zeus assumed to court the princess Leda, or alternatively Orpheus transformed after death and placed beside his lyre in the sky. Its distinctive cross shape has also been called the Northern Cross since medieval times.",
    "Deneb is one of the most luminous stars visible to the naked eye — roughly 200,000 times the Sun's luminosity. Only its extreme distance of about 2,600 light-years keeps it from outshining everything in the night sky."
  ],
  "Lyra": [
    "Lyra represents the lyre of Orpheus, the greatest musician in Greek mythology. His music charmed stones, beasts, and rivers alike. After his death the Muses placed his lyre among the stars. Vega was the North Star around 12,000 BCE and will be again in roughly 14,000 CE.",
    "Vega was the first star — other than the Sun — to be photographed, in 1850. It rotates so rapidly it bulges significantly at its equator. Its brightness and proximity (25 light-years) make it a standard calibration point for measuring stellar magnitudes."
  ],
  "Aquila": [
    "Aquila, the eagle, was Zeus's loyal bird and divine messenger. The eagle was tasked with stealing the beautiful youth Ganymede to serve as cupbearer of the gods. Altair, its bright eye, is one of the closest naked-eye stars at just 17 light-years.",
    "In Japanese tradition, Altair is Hikoboshi, the Cowherd Star, separated from Vega (Orihime, the Weaver) by the Milky Way, united once a year during the Tanabata festival. The Summer Triangle — Vega, Deneb, and Altair — dominates northern summer skies."
  ],
  "Gemini": [
    "Castor and Pollux, the twin sons of Leda, represent fraternal devotion. Pollux was immortal (son of Zeus) while Castor was mortal. When Castor died, Pollux shared his immortality, and Zeus placed them together as stars. They became the patron saints of sailors.",
    "The star Castor appears single to the naked eye but is actually a sextuple star system — three pairs of binary stars orbiting each other. It stands 51 light-years away and unfolds its complexity only under telescopic examination."
  ],
  "Taurus": [
    "Taurus represents the bull form Zeus took to abduct the Phoenician princess Europa. He transformed himself into a gentle white bull, carried her to Crete, and fathered King Minos. The Pleiades and Hyades clusters within Taurus were associated with rain and seafaring.",
    "The Pleiades — the Seven Sisters — have been recognized as a group across nearly every human culture. The constellation Taurus appears in the Lascaux cave paintings from around 17,000 BCE, making it one of the oldest known star maps in existence."
  ],
  "Virgo": [
    "Virgo is typically identified as Demeter or her daughter Persephone. When Persephone descends to the underworld, Demeter disappears below the horizon and crops wither — winter. Her return brings spring. Spica guided Hipparchus to discover precession of the equinoxes around 127 BCE.",
    "The Virgo Cluster, in the direction of this constellation, is the nearest large galaxy cluster — about 54 million light-years away, containing over 1,300 galaxies. Its gravitational influence dominates our Local Group, drawing the Milky Way and Andromeda toward it."
  ],
  "Boötes": [
    "Boötes the herdsman is sometimes identified as Arcas, son of Callisto and Zeus — the same Arcas who nearly killed his own mother when she was transformed into a bear. He is often depicted driving the bears around the celestial pole.",
    "In 1933, light from Arcturus triggered floodlights to open the Chicago World's Fair. The star was selected because its 36-light-year distance meant the light had left during the previous Chicago exposition of 1893 — a poetic closing of the loop."
  ],
  "Perseus": [
    "Perseus slew the Gorgon Medusa with a mirrored shield, then rescued Andromeda — chained as a sacrifice to the sea monster Cetus — by turning the monster to stone with Medusa's severed head. Algol, 'the demon star,' represents Medusa's blinking eye.",
    "Algol's reputation as a 'winking demon' was explained in 1783 by John Goodricke, who deduced it was an eclipsing binary — a dimmer companion passes in front of the brighter star every 2.87 days. Goodricke was deaf from birth and made this discovery at age 18."
  ],
  "Auriga": [
    "Auriga the charioteer is linked to Erichthonius, mythical king of Athens and inventor of the four-horse chariot. He is depicted holding the reins in one hand and a she-goat (Capella) with her kids in the other. Capella is actually a pair of giant stars orbiting each other.",
    "The Auriga Milky Way is among the richest regions of sky for open star clusters — M36, M37, and M38 are visible in binoculars within this constellation. Sailors used Capella as a year-round navigation reference because it is circumpolar from northern latitudes."
  ],
  "Canis Major": [
    "Canis Major is Orion's loyal hunting dog, following him across the sky. It contains Sirius — 'the scorching one' — the brightest star in the night sky. The ancient Egyptians called it Sopdet and aligned the Great Pyramid's shafts toward its heliacal rising.",
    "The ancient Egyptian year began when Sirius rose just before the Sun on the summer solstice, signaling the Nile's imminent flood. This 'Sothic cycle' of 1,461 Egyptian years formed the basis of their calendar. Sirius is only 8.6 light-years away — our seventh-nearest stellar neighbor."
  ],
  "Aquarius": [
    "Aquarius the water-bearer is associated with Ganymede, the beautiful Trojan youth abducted by Zeus's eagle to serve as cupbearer of the gods. In Babylonian tradition he was the god Ea, 'Lord of the Abyss,' who warned the hero Utnapishtim about the coming great flood.",
    "The 'Age of Aquarius' refers to the roughly 2,000-year precession period when the vernal equinox lies in Aquarius. Due to Earth's slow axial wobble, the equinox is currently transitioning from Pisces into Aquarius — though astronomers and astrologers disagree on when this officially occurs."
  ],
  "Sagittarius": [
    "Sagittarius the archer is identified as the centaur Crotus, son of the god Pan and an expert archer who invented hunting on horseback. He aims his arrow at Scorpius. The center of the Milky Way lies in the direction of Sagittarius, dense with star clouds and nebulae.",
    "Sagittarius A*, the supermassive black hole at the center of our galaxy, lurks 26,000 light-years away in this direction. It has a mass of 4 million Suns. The Event Horizon Telescope captured the first image of its shadow in 2022, confirming decades of inference from nearby star orbits."
  ],
  "Hercules": [
    "Hercules was the greatest hero of Greek mythology, known for twelve labors: slaying the Nemean Lion and Lernaean Hydra, cleaning the Augean Stables in a single day, and more. He earned immortality after death and a permanent place among the stars.",
    "The Hercules Cluster (M13) — one of the finest globular clusters in the northern sky — contains roughly 300,000 stars in a sphere 145 light-years across. In 1974, the Arecibo radio telescope aimed humanity's first intentional interstellar message directly at M13."
  ],
  "Ursa Minor": [
    "Ursa Minor contains Polaris, the current North Star, positioned within 1° of true north. In Greek myth it is Arcas, son of Zeus and Callisto, placed in the heavens to reunite with his mother. The pole star has shifted over millennia — Thuban in Draco was Egypt's North Star.",
    "Polaris is not a single star but a triple system: a supergiant primary and two smaller companions. It is the nearest Cepheid variable to Earth — a pulsating star whose clockwork brightness cycles are used as a 'standard candle' to measure cosmic distances."
  ],
  "Andromeda": [
    "Princess Andromeda was chained to a sea cliff as a sacrifice to the monster Cetus — punishment for her mother Cassiopeia's boast. Perseus rescued her, petrifying the monster with Medusa's head. Her constellation lies between her mother and her hero in the sky.",
    "The Andromeda Galaxy (M31) — the nearest large galaxy at 2.5 million light-years — is visible to the naked eye within this constellation as a faint smear. It is on a collision course with the Milky Way, expected to merge in about 4.5 billion years into a galaxy sometimes called 'Milkomeda.'"
  ]
}
```

- [ ] **Step 3: Commit**

```bash
git add data/constellations.json data/mythology.json
git commit -m "feat: add constellation stick-figure and mythology data files"
```

---

## Task 3: Sky Map Generator (TDD)

**Files:**
- Create: `tests/test_skymap.py`
- Create: `app/skymap.py`

- [ ] **Step 1: Write failing tests in `tests/test_skymap.py`**

```python
import pytest
from app.skymap import generate_skymap, az_alt_to_xy, star_radius, CX, CY, R


def test_zenith_star_projects_to_center():
    stars = [{"alt": 90.0, "az": 0.0, "magnitude": 1.0, "hip_id": 1}]
    svg = generate_skymap(stars, [])
    assert f'cx="{CX:.1f}" cy="{CY:.1f}"' in svg


def test_north_horizon_star_projects_to_top():
    stars = [{"alt": 0.0, "az": 0.0, "magnitude": 1.0, "hip_id": 1}]
    svg = generate_skymap(stars, [])
    expected_y = CY - R
    assert f'cy="{expected_y:.1f}"' in svg


def test_bright_star_larger_than_dim():
    # mag 0 → r=3.5; mag 5 → r=1.0
    assert star_radius(0.0) == pytest.approx(3.5)
    assert star_radius(5.0) == pytest.approx(1.0)


def test_very_dim_star_clamped_to_minimum():
    assert star_radius(10.0) == pytest.approx(0.5)


def test_empty_sky_returns_valid_svg():
    svg = generate_skymap([], [])
    assert svg.startswith("<svg")
    assert svg.strip().endswith("</svg>")


def test_constellation_line_drawn_when_both_stars_visible():
    stars = [
        {"alt": 45.0, "az": 0.0, "magnitude": 2.0, "hip_id": 1},
        {"alt": 45.0, "az": 90.0, "magnitude": 2.0, "hip_id": 2},
    ]
    lines = [{"hip_a": 1, "hip_b": 2}]
    svg = generate_skymap(stars, lines)
    assert "<line" in svg


def test_constellation_line_omitted_when_star_missing():
    stars = [{"alt": 45.0, "az": 0.0, "magnitude": 2.0, "hip_id": 1}]
    lines = [{"hip_a": 1, "hip_b": 999}]  # hip_b not in star list
    svg = generate_skymap(stars, lines)
    assert "<line" not in svg


def test_cardinal_labels_present():
    svg = generate_skymap([], [])
    for label in ("N", "S", "E", "W"):
        assert f">{label}<" in svg
```

- [ ] **Step 2: Run tests — confirm all fail**

```bash
pip install -r requirements-dev.txt
pytest tests/test_skymap.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `app.skymap` does not exist yet.

- [ ] **Step 3: Write `app/skymap.py`**

```python
import math

VIEWBOX_SIZE = 400
CX = VIEWBOX_SIZE / 2        # 200.0
CY = VIEWBOX_SIZE / 2        # 200.0
R  = VIEWBOX_SIZE / 2 - 10   # 190.0  (10px margin inside circle)


def az_alt_to_xy(az_deg: float, alt_deg: float) -> tuple[float, float]:
    """Project alt/az to SVG x,y. Zenith → center; horizon → edge circle."""
    r = (90.0 - alt_deg) / 90.0 * R
    az_rad = math.radians(az_deg)
    x = CX + r * math.sin(az_rad)
    y = CY - r * math.cos(az_rad)
    return x, y


def star_radius(magnitude: float) -> float:
    return max(0.5, 3.5 - magnitude * 0.5)


def generate_skymap(
    stars: list[dict],
    const_lines: list[dict],
) -> str:
    """
    stars:       [{"alt": float, "az": float, "magnitude": float, "hip_id": int}, ...]
    const_lines: [{"hip_a": int, "hip_b": int}, ...]
    Returns a self-contained SVG string.
    """
    hip_xy: dict[int, tuple[float, float]] = {
        s["hip_id"]: az_alt_to_xy(s["az"], s["alt"]) for s in stars
    }

    lines_svg = []
    for seg in const_lines:
        a, b = seg["hip_a"], seg["hip_b"]
        if a in hip_xy and b in hip_xy:
            x1, y1 = hip_xy[a]
            x2, y2 = hip_xy[b]
            lines_svg.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="#3a5a3a" stroke-width="0.8" stroke-opacity="0.7"/>'
            )

    stars_svg = []
    for s in stars:
        x, y = hip_xy[s["hip_id"]]
        r = star_radius(s["magnitude"])
        stars_svg.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="#c8e6c8" fill-opacity="0.9"/>'
        )

    cardinals = [("N", 0), ("E", 90), ("S", 180), ("W", 270)]
    cardinal_svg = []
    for label, az in cardinals:
        x, y = az_alt_to_xy(az, 0.0)
        scale = (R + 12) / R
        lx = CX + (x - CX) * scale
        ly = CY + (y - CY) * scale
        cardinal_svg.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" fill="#556655" font-size="10" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'font-family="monospace">{label}</text>'
        )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {VIEWBOX_SIZE} {VIEWBOX_SIZE}" '
        f'width="{VIEWBOX_SIZE}" height="{VIEWBOX_SIZE}" style="background:#050510">',
        f'<circle cx="{CX:.1f}" cy="{CY:.1f}" r="{R:.1f}" fill="#050510" stroke="#223322" stroke-width="1"/>',
        *lines_svg,
        *stars_svg,
        *cardinal_svg,
        "</svg>",
    ]
    return "\n".join(parts)
```

- [ ] **Step 4: Run tests — confirm all pass**

```bash
pytest tests/test_skymap.py -v
```

Expected: 8 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/skymap.py tests/test_skymap.py
git commit -m "feat: SVG sky map generator with alt/az projection"
```

---

## Task 4: Astronomy — Pure Helpers (TDD)

These two functions require no skyfield and are fully testable without data files.

**Files:**
- Create: `tests/test_astronomy.py`
- Create: `app/astronomy.py` (pure helpers only; skyfield functions added in Task 5)

- [ ] **Step 1: Write failing tests in `tests/test_astronomy.py`**

```python
import pytest
from app.astronomy import phase_name_from_elongation, pick_mythology


# ── phase_name_from_elongation ────────────────────────────────────────────────

@pytest.mark.parametrize("elongation,expected_name,expected_glyph", [
    (0.0,   "New Moon",        "🌑"),
    (10.0,  "New Moon",        "🌑"),
    (45.0,  "Waxing Crescent", "🌒"),
    (90.0,  "First Quarter",   "🌓"),
    (135.0, "Waxing Gibbous",  "🌔"),
    (180.0, "Full Moon",       "🌕"),
    (225.0, "Waning Gibbous",  "🌖"),
    (270.0, "Last Quarter",    "🌗"),
    (315.0, "Waning Crescent", "🌘"),
    (359.9, "Waning Crescent", "🌘"),
])
def test_phase_name_from_elongation(elongation, expected_name, expected_glyph):
    name, glyph = phase_name_from_elongation(elongation)
    assert name == expected_name
    assert glyph == expected_glyph


# ── pick_mythology ────────────────────────────────────────────────────────────

MYTH = {
    "Orion":  ["Orion fact A", "Orion fact B"],
    "Leo":    ["Leo fact A"],
    "Gemini": ["Gemini fact A", "Gemini fact B"],
}


def test_mythology_restricts_to_visible_constellations():
    result = pick_mythology(["Orion"], MYTH, date_str="2026-01-01")
    assert result["constellation"] == "Orion"


def test_mythology_falls_back_when_no_visible_match():
    result = pick_mythology([], MYTH, date_str="2026-01-01")
    assert result["constellation"] in MYTH


def test_mythology_falls_back_when_visible_have_no_entry():
    result = pick_mythology(["Taurus"], MYTH, date_str="2026-01-01")
    assert result["constellation"] in MYTH


def test_mythology_is_deterministic_for_same_date():
    r1 = pick_mythology(["Orion", "Leo", "Gemini"], MYTH, date_str="2026-06-10")
    r2 = pick_mythology(["Orion", "Leo", "Gemini"], MYTH, date_str="2026-06-10")
    assert r1 == r2


def test_mythology_result_has_required_keys():
    result = pick_mythology(["Orion"], MYTH, date_str="2026-06-10")
    assert "constellation" in result
    assert "text" in result
    assert isinstance(result["text"], str)
    assert len(result["text"]) > 0


def test_mythology_text_belongs_to_chosen_constellation():
    result = pick_mythology(["Orion", "Leo"], MYTH, date_str="2026-06-10")
    expected_texts = MYTH[result["constellation"]]
    assert result["text"] in expected_texts
```

- [ ] **Step 2: Run tests — confirm all fail**

```bash
pytest tests/test_astronomy.py -v
```

Expected: `ImportError` — `app.astronomy` does not exist yet.

- [ ] **Step 3: Write `app/astronomy.py` (pure helpers only)**

```python
import math
import hashlib
import os
from datetime import date as _date

SKYFIELD_DATA_DIR = os.environ.get("SKYFIELD_DATA", "/skyfield-data")

# Lazy-loaded skyfield globals (populated in Task 5 functions)
_loader = None
_eph = None
_stars_df = None

# ── Phase mapping ─────────────────────────────────────────────────────────────

_PHASES: list[tuple[float, str, str]] = [
    (22.5,  "New Moon",        "🌑"),
    (67.5,  "Waxing Crescent", "🌒"),
    (112.5, "First Quarter",   "🌓"),
    (157.5, "Waxing Gibbous",  "🌔"),
    (202.5, "Full Moon",       "🌕"),
    (247.5, "Waning Gibbous",  "🌖"),
    (292.5, "Last Quarter",    "🌗"),
    (337.5, "Waning Crescent", "🌘"),
    (360.0, "New Moon",        "🌑"),
]


def phase_name_from_elongation(elongation: float) -> tuple[str, str]:
    """Map elongation in degrees [0, 360) to (phase_name, glyph)."""
    for threshold, name, glyph in _PHASES:
        if elongation < threshold:
            return name, glyph
    return "New Moon", "🌑"


# ── Mythology selection ───────────────────────────────────────────────────────

def pick_mythology(
    visible_names: list[str],
    mythology: dict[str, list[str]],
    date_str: str | None = None,
) -> dict[str, str]:
    """
    Pick one mythology entry deterministically by date.
    Candidates are filtered to visible constellations that have entries;
    falls back to the full mythology dict if none match.
    """
    if date_str is None:
        date_str = _date.today().isoformat()
    seed = int(hashlib.md5(date_str.encode()).hexdigest(), 16)

    candidates = [n for n in visible_names if n in mythology]
    if not candidates:
        candidates = list(mythology.keys())

    chosen = candidates[seed % len(candidates)]
    entries = mythology[chosen]
    entry = entries[(seed // max(len(candidates), 1)) % len(entries)]
    return {"constellation": chosen, "text": entry}
```

- [ ] **Step 4: Run tests — confirm all pass**

```bash
pytest tests/test_astronomy.py -v
```

Expected: 11 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/astronomy.py tests/test_astronomy.py
git commit -m "feat: astronomy pure helpers — phase mapping and mythology selection"
```

---

## Task 5: Astronomy — Skyfield Computations

Add `get_moon_data`, `get_visible_constellations`, and `get_skymap_stars` to `app/astronomy.py`. These require the pre-downloaded skyfield data files and are covered by integration tests in Task 6 (where skyfield is mocked at the API boundary).

**Files:**
- Modify: `app/astronomy.py`

- [ ] **Step 1: Add lazy skyfield loaders to `app/astronomy.py`**

Append after the existing pure helpers:

```python
# ── Skyfield lazy loaders ─────────────────────────────────────────────────────

def _get_loader():
    global _loader
    if _loader is None:
        from skyfield.api import Loader
        _loader = Loader(SKYFIELD_DATA_DIR)
    return _loader


def _get_eph():
    global _eph
    if _eph is None:
        _eph = _get_loader()("de421.bsp")
    return _eph


def _get_stars_df():
    global _stars_df
    if _stars_df is None:
        from skyfield.data import hipparcos
        with _get_loader().open("hip_main.dat") as f:
            _stars_df = hipparcos.load_dataframe(f)
    return _stars_df
```

- [ ] **Step 2: Add `get_moon_data` to `app/astronomy.py`**

```python
def get_moon_data(ts, lat: float, lon: float) -> dict:
    """Return moon phase, illumination, and rise/set/transit times (UTC strings)."""
    from skyfield.api import wgs84
    from skyfield import almanac
    from skyfield.framelib import ecliptic_J2000_frame
    from skyfield.searchlib import find_maxima

    eph = _get_eph()
    t = ts.now()

    # Phase angle via ecliptic longitude difference
    earth = eph["earth"]
    e = earth.at(t)
    moon_ecl = e.observe(eph["moon"]).apparent().frame_latlon(ecliptic_J2000_frame)
    sun_ecl  = e.observe(eph["sun"]).apparent().frame_latlon(ecliptic_J2000_frame)
    elongation = (moon_ecl[1].degrees - sun_ecl[1].degrees) % 360
    illumination = round((1 - math.cos(math.radians(elongation))) / 2 * 100, 1)
    phase_name, phase_glyph = phase_name_from_elongation(elongation)

    # Rise / set
    location = wgs84.latlon(lat, lon)
    t0 = ts.now()
    t1 = ts.tt_jd(t0.tt + 1.0)
    rise_str = set_str = transit_str = None

    try:
        f = almanac.risings_and_settings(eph, eph["moon"], location)
        times, events = almanac.find_discrete(t0, t1, f)
        for t_evt, evt in zip(times, events):
            if evt == 1 and rise_str is None:
                rise_str = t_evt.utc_strftime("%H:%M")
            elif evt == 0 and set_str is None:
                set_str = t_evt.utc_strftime("%H:%M")
    except Exception:
        pass  # polar conditions — leave None

    # Transit (altitude maximum)
    try:
        observer = earth + location

        def _moon_alt(t_inner):
            alt, _, _ = observer.at(t_inner).observe(eph["moon"]).apparent().altaz()
            return alt.degrees

        _moon_alt.rough_period = 0.5
        transit_times, _ = find_maxima(t0, t1, _moon_alt)
        if len(transit_times) > 0:
            transit_str = transit_times[0].utc_strftime("%H:%M")
    except Exception:
        pass

    return {
        "phase_name":       phase_name,
        "phase_glyph":      phase_glyph,
        "illumination_pct": illumination,
        "rise":             rise_str,
        "set":              set_str,
        "transit":          transit_str,
    }
```

- [ ] **Step 3: Add `get_visible_constellations` to `app/astronomy.py`**

```python
def get_visible_constellations(
    ts, lat: float, lon: float, constellation_data: list[dict]
) -> list[dict]:
    """
    Return constellations whose average stick-figure star altitude > -10°.
    above_horizon is True if at least one defining star is above 0°.
    """
    from skyfield.api import wgs84, Star

    eph = _get_eph()
    stars_df = _get_stars_df()
    observer = eph["earth"] + wgs84.latlon(lat, lon)
    t = ts.now()

    visible = []
    for const in constellation_data:
        alts = []
        for hip_id in const["hip_ids"]:
            if hip_id in stars_df.index:
                star = Star.from_dataframe(stars_df.loc[hip_id:hip_id])
                alt, _, _ = observer.at(t).observe(star).apparent().altaz()
                alts.append(float(alt.degrees))
        if alts and (sum(alts) / len(alts)) > -10.0:
            visible.append({
                "name":          const["name"],
                "abbr":          const["abbr"],
                "above_horizon": any(a > 0 for a in alts),
            })
    return visible
```

- [ ] **Step 4: Add `get_skymap_stars` to `app/astronomy.py`**

```python
def get_skymap_stars(
    ts, lat: float, lon: float, constellation_data: list[dict]
) -> tuple[list[dict], list[dict]]:
    """
    Return (star_list, const_lines) for sky map rendering.
    star_list:   [{"alt", "az", "magnitude", "hip_id"}, ...]  — above horizon, mag ≤ 5.5
    const_lines: [{"hip_a", "hip_b"}, ...]  — only segments where both stars are above horizon
    """
    from skyfield.api import wgs84, Star

    eph = _get_eph()
    stars_df = _get_stars_df()
    observer = eph["earth"] + wgs84.latlon(lat, lon)
    t = ts.now()

    bright = stars_df[stars_df["magnitude"] <= 5.5]
    stars_obj = Star.from_dataframe(bright)
    astrometric = observer.at(t).observe(stars_obj)
    alt_arr, az_arr, _ = astrometric.apparent().altaz()

    star_list: list[dict] = []
    hip_above: set[int] = set()

    for i, (hip_id, row) in enumerate(bright.iterrows()):
        a = float(alt_arr.degrees[i])
        z = float(az_arr.degrees[i])
        if a > 0:
            star_list.append({
                "alt":       a,
                "az":        z,
                "magnitude": float(row["magnitude"]),
                "hip_id":    int(hip_id),
            })
            hip_above.add(int(hip_id))

    const_lines: list[dict] = []
    for const in constellation_data:
        for hip_a, hip_b in const["lines"]:
            if hip_a in hip_above and hip_b in hip_above:
                const_lines.append({"hip_a": hip_a, "hip_b": hip_b})

    return star_list, const_lines
```

- [ ] **Step 5: Verify existing tests still pass**

```bash
pytest tests/test_astronomy.py tests/test_skymap.py -v
```

Expected: all 19 tests PASSED (no skyfield calls made).

- [ ] **Step 6: Commit**

```bash
git add app/astronomy.py
git commit -m "feat: astronomy skyfield computations — moon, constellations, sky map stars"
```

---

## Task 6: FastAPI App (TDD)

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_main.py`
- Create: `app/main.py`

- [ ] **Step 1: Write `tests/conftest.py`**

```python
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

MOCK_MOON = {
    "phase_name": "Full Moon",
    "phase_glyph": "🌕",
    "illumination_pct": 100.0,
    "rise": "18:00",
    "set": "06:00",
    "transit": "00:00",
}
MOCK_CONSTELLATIONS = [
    {"name": "Orion", "abbr": "Ori", "above_horizon": True},
    {"name": "Gemini", "abbr": "Gem", "above_horizon": True},
]
MOCK_MYTHOLOGY = {"constellation": "Orion", "text": "Orion was a hunter."}
MOCK_SVG = "<svg></svg>"


@pytest.fixture()
def client():
    # Patch skyfield-dependent functions before importing app.main
    with patch("app.astronomy.get_moon_data", return_value=MOCK_MOON), \
         patch("app.astronomy.get_visible_constellations", return_value=MOCK_CONSTELLATIONS), \
         patch("app.astronomy.get_skymap_stars", return_value=([], [])), \
         patch("app.skymap.generate_skymap", return_value=MOCK_SVG):
        from fastapi.testclient import TestClient
        from app.main import app
        yield TestClient(app)
```

- [ ] **Step 2: Write failing tests in `tests/test_main.py`**

```python
import pytest
from tests.conftest import MOCK_MOON, MOCK_CONSTELLATIONS, MOCK_MYTHOLOGY, MOCK_SVG
from unittest.mock import patch


def test_root_returns_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_root_html_contains_fallback_script(client):
    resp = client.get("/")
    assert "window.__FALLBACK__" in resp.text


def test_sky_api_success(client):
    with patch("app.astronomy.get_moon_data", return_value=MOCK_MOON), \
         patch("app.astronomy.get_visible_constellations", return_value=MOCK_CONSTELLATIONS), \
         patch("app.astronomy.get_skymap_stars", return_value=([], [])), \
         patch("app.skymap.generate_skymap", return_value=MOCK_SVG), \
         patch("app.astronomy.pick_mythology", return_value=MOCK_MYTHOLOGY):
        resp = client.get("/api/sky?lat=40.71&lon=-74.01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["moon"]["phase_name"] == "Full Moon"
    assert isinstance(data["constellations"], list)
    assert data["skymap_svg"] == MOCK_SVG
    assert data["mythology"]["constellation"] == "Orion"
    assert data["location"] == {"lat": 40.71, "lon": -74.01}


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
```

- [ ] **Step 3: Run tests — confirm they fail**

```bash
pytest tests/test_main.py -v
```

Expected: `ImportError` — `app.main` does not exist yet.

- [ ] **Step 4: Write `app/main.py`**

```python
import os
import json
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from skyfield.api import load as skyfield_load

from .astronomy import (
    get_moon_data,
    get_visible_constellations,
    get_skymap_stars,
    pick_mythology,
)
from .skymap import generate_skymap

_ROOT     = Path(__file__).parent.parent   # moondocker/
DATA_DIR  = _ROOT / "data"
STATIC_DIR = Path(__file__).parent / "static"

with open(DATA_DIR / "constellations.json") as _f:
    CONSTELLATION_DATA: list[dict] = json.load(_f)

with open(DATA_DIR / "mythology.json") as _f:
    MYTHOLOGY_DATA: dict[str, list[str]] = json.load(_f)

FALLBACK_LAT = os.environ.get("LAT", "")
FALLBACK_LON = os.environ.get("LON", "")

ts = skyfield_load.timescale()

app = FastAPI(title="moondocker")


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    html = (STATIC_DIR / "index.html").read_text()
    lat_val = FALLBACK_LAT if FALLBACK_LAT else "null"
    lon_val = FALLBACK_LON if FALLBACK_LON else "null"
    injection = f'<script>window.__FALLBACK__={{"lat":{lat_val},"lon":{lon_val}}}</script>'
    return html.replace("</head>", f"{injection}\n</head>")


@app.get("/api/sky")
async def get_sky(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
) -> dict:
    moon        = get_moon_data(ts, lat, lon)
    consts      = get_visible_constellations(ts, lat, lon, CONSTELLATION_DATA)
    myth        = pick_mythology([c["name"] for c in consts], MYTHOLOGY_DATA)
    stars, segs = get_skymap_stars(ts, lat, lon, CONSTELLATION_DATA)
    svg         = generate_skymap(stars, segs)

    return {
        "moon":          moon,
        "constellations": consts,
        "skymap_svg":    svg,
        "mythology":     myth,
        "location":      {"lat": lat, "lon": lon},
    }


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
```

- [ ] **Step 5: Run tests — confirm all pass**

```bash
pytest tests/test_main.py -v
```

Expected: 8 tests PASSED. (Tests for static files will fail until Task 7 creates them — that is expected. Run Task 7 before checking those two.)

- [ ] **Step 6: Commit**

```bash
git add app/main.py tests/conftest.py tests/test_main.py
git commit -m "feat: FastAPI app with /api/sky endpoint and static file serving"
```

---

## Task 7: Frontend

**Files:**
- Create: `app/static/index.html`
- Create: `app/static/style.css`
- Create: `app/static/app.js`

- [ ] **Step 1: Write `app/static/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>moondocker</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <header>
    <pre id="title"> ᛗᛟᛟᚾᛞᛟᚲᚲᛖᚱ</pre>
  </header>

  <div id="loading" class="panel">
    <div class="panel-body">Locating sky data...</div>
  </div>

  <div id="error" class="panel error hidden">
    <div class="panel-header">ᛖᚱᚱᛟᚱ</div>
    <div id="error-msg" class="panel-body"></div>
  </div>

  <div id="content" class="hidden">
    <div class="panel">
      <div class="panel-header">ᛗᛟᛟᚾ</div>
      <div class="panel-body">
        <div id="moon-phase"></div>
        <div id="moon-times"></div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-header">ᚾᛁᚷᚺᛏ ᛋᚲᚤ</div>
      <div id="skymap" class="panel-body skymap-body"></div>
    </div>

    <div class="panel">
      <div class="panel-header">ᚲᛟᚾᛋᛏᛖᛚᛚᚨᛏᛁᛟᚾᛋ</div>
      <pre id="constellations-list" class="panel-body"></pre>
    </div>

    <div class="panel">
      <div id="mythology-header" class="panel-header">ᛚᛖᚷᛖᚾᛞ</div>
      <div id="mythology-text" class="panel-body"></div>
    </div>
  </div>

  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `app/static/style.css`**

```css
:root {
  --bg:      #0a0a0f;
  --surface: #0d0d14;
  --border:  #1e2e1e;
  --header:  #3a5a3a;
  --text:    #8fbc8f;
  --dim:     #4a6a4a;
  --accent:  #c8e6c8;
  --error:   #8b3a3a;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: 'Courier New', Courier, monospace;
  font-size: 14px;
  line-height: 1.6;
  padding: 1.2rem;
  max-width: 680px;
  margin: 0 auto;
}

#title {
  color: var(--accent);
  text-align: center;
  font-size: 1.3rem;
  letter-spacing: 0.35em;
  margin-bottom: 1.4rem;
}

.panel {
  border: 1px solid var(--border);
  margin-bottom: 1rem;
  background: var(--surface);
}

.panel-header {
  background: var(--header);
  color: var(--accent);
  padding: 0.2rem 0.7rem;
  font-size: 0.85rem;
  letter-spacing: 0.18em;
  border-bottom: 1px solid var(--border);
}

.panel-body {
  padding: 0.65rem 0.9rem;
}

.skymap-body {
  display: flex;
  justify-content: center;
  padding: 0.5rem;
}

#skymap svg {
  max-width: 100%;
  height: auto;
}

.panel.error .panel-header { background: var(--error); }
.panel.error .panel-body   { color: #c88; }

.hidden { display: none !important; }
```

- [ ] **Step 3: Write `app/static/app.js`**

```javascript
function renderMoon(moon) {
  const phase = document.getElementById('moon-phase');
  phase.textContent =
    'Phase: ' + moon.phase_name + '  ' + moon.phase_glyph +
    '   Illumination: ' + moon.illumination_pct.toFixed(1) + '%';

  const times = document.getElementById('moon-times');
  times.textContent =
    'Rise: ' + (moon.rise || '--:--') +
    '   Transit: ' + (moon.transit || '--:--') +
    '   Set: ' + (moon.set || '--:--') + ' (UTC)';
}

function renderConstellations(constellations) {
  const lines = constellations.map(function(c) {
    var status = c.above_horizon ? '▲ ABOVE' : '▽ BELOW';
    var label  = (c.name + ' (' + c.abbr + ')').padEnd(24);
    return label + '  ' + status;
  });
  document.getElementById('constellations-list').textContent = lines.join('\n');
}

function renderMythology(mythology) {
  document.getElementById('mythology-header').textContent =
    'ᛚᛖᛖᛖᛚ : ' + mythology.constellation;
  document.getElementById('mythology-text').textContent = mythology.text;
}

function showError(msg) {
  document.getElementById('loading').classList.add('hidden');
  document.getElementById('error-msg').textContent = msg;
  document.getElementById('error').classList.remove('hidden');
}

async function loadSky(lat, lon) {
  const resp = await fetch('/api/sky?lat=' + lat + '&lon=' + lon);
  if (!resp.ok) throw new Error('API returned ' + resp.status);
  return resp.json();
}

async function init() {
  var lat, lon;

  try {
    var pos = await new Promise(function(resolve, reject) {
      navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 8000 });
    });
    lat = pos.coords.latitude;
    lon = pos.coords.longitude;
  } catch (_) {
    var fb = window.__FALLBACK__ || {};
    if (fb.lat == null || fb.lon == null) {
      showError(
        'Location unavailable.\n' +
        'Set LAT and LON environment variables and restart the container:\n\n' +
        '  docker run -p 7432:7432 -e LAT=40.71 -e LON=-74.01 moondocker'
      );
      return;
    }
    lat = fb.lat;
    lon = fb.lon;
  }

  try {
    var data = await loadSky(lat, lon);
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('content').classList.remove('hidden');
    renderMoon(data.moon);
    document.getElementById('skymap').innerHTML = data.skymap_svg;
    renderConstellations(data.constellations);
    renderMythology(data.mythology);
  } catch (e) {
    showError('Failed to load sky data: ' + e.message);
  }
}

init();
```

- [ ] **Step 4: Run the full test suite**

```bash
pytest -v
```

Expected: all tests PASSED (including the two static-file tests that were skipped before).

- [ ] **Step 5: Commit**

```bash
git add app/static/index.html app/static/style.css app/static/app.js
git commit -m "feat: ASCII/runic frontend — HTML shell, dark monospace theme, geolocation JS"
```

---

## Task 8: Docker Build and Smoke Test

**Files:**
- No new files; verifies the full stack works inside the container.

- [ ] **Step 1: Build the image**

```bash
docker build -t moondocker .
```

Expected: build succeeds; the skyfield data download step takes 1-3 minutes on first run (de421.bsp is ~17 MB; hip_main.dat is ~2 MB). Subsequent builds use the Docker layer cache.

- [ ] **Step 2: Run the container**

```bash
docker run -p 7432:7432 -e LAT=40.7128 -e LON=-74.0060 moondocker
```

Expected log line:

```
INFO:     Uvicorn running on http://0.0.0.0:7432 (Press CTRL+C to quit)
```

- [ ] **Step 3: Smoke test the API (new terminal)**

```bash
curl -s "http://localhost:7432/api/sky?lat=40.7128&lon=-74.0060" | python3 -m json.tool | head -30
```

Expected: JSON with keys `moon`, `constellations`, `skymap_svg`, `mythology`, `location`. The `moon.phase_name` should be one of the eight phase names. `constellations` should be a non-empty list. `skymap_svg` should start with `<svg`.

- [ ] **Step 4: Smoke test the HTML root**

```bash
curl -s "http://localhost:7432/" | grep -o "window.__FALLBACK__.*"
```

Expected:

```
window.__FALLBACK__={"lat":40.7128,"lon":-74.006}</script>
```

- [ ] **Step 5: Test LAT/LON fallback injection with no values**

```bash
docker run -p 7433:7432 moondocker &
curl -s "http://localhost:7433/" | grep "__FALLBACK__"
```

Expected:

```
window.__FALLBACK__={"lat":null,"lon":null}</script>
```

Stop the container after verifying.

- [ ] **Step 6: Verify docker-compose works**

```bash
docker compose up -d
curl -s "http://localhost:7432/api/sky?lat=51.5&lon=-0.12" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['moon']['phase_name'], d['mythology']['constellation'])"
docker compose down
```

Expected: prints a phase name and a constellation name, e.g. `Waxing Gibbous Orion`.

- [ ] **Step 7: Final commit**

```bash
git add .
git commit -m "feat: end-to-end Docker build verified — moondocker ready for use"
```

---

## Self-Review Checklist

| Spec requirement | Task |
|---|---|
| Browser geolocation with LAT/LON env var fallback | Task 6 (injection), Task 7 (app.js) |
| Moon phase name, glyph, illumination | Task 4 + Task 5 |
| Moon rise/set/transit (UTC) | Task 5 |
| Visible constellations for location | Task 5 |
| SVG sky map, alt/az projection, star sizing | Task 3 + Task 5 |
| Constellation stick-figure lines on sky map | Task 2 + Task 3 |
| Mythology trivia, date-seeded, visible constellations only | Task 4 |
| Mythology falls back when no visible constellation has an entry | Task 4 |
| ASCII/runic theme with box-drawing borders and rune headers | Task 7 |
| Single container, port 7432 | Task 1 |
| Skyfield data pre-downloaded at build time (no runtime network) | Task 1 |
| docker-compose drop-in | Task 1 + Task 8 |
| 422 on invalid lat/lon | Task 6 |
| Polar conditions handled gracefully (None rise/set) | Task 5 |
