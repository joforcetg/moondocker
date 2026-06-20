# Contributing

## Setup

```bash
git clone https://github.com/joforcetg/moondocker
cd moondocker
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

## Run tests

Tests mock all skyfield calls — no data download needed.

```bash
.venv/bin/python -m pytest -v
```

## Run the app locally

Download skyfield data once:

```bash
SKYFIELD_DATA=.skyfield-data .venv/bin/python -c "
from skyfield.api import Loader
from skyfield.data import hipparcos
load = Loader('.skyfield-data')
load('de421.bsp')
hipparcos.load_dataframe(load.open(hipparcos.URL))
"
```

Then run:

```bash
SKYFIELD_DATA=.skyfield-data .venv/bin/python -m uvicorn app.main:app --port 7432
```

## Pull requests

- Small, focused commits
- All tests must pass before opening a PR
- No new dependencies without discussion — open an issue first
- Patch `app.main.*` names in tests, not source modules (see `tests/conftest.py`)
