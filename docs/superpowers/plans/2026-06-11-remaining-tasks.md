# moondocker — Remaining Tasks & Pre-flight Fixes

> Addendum to `2026-06-10-moondocker.md`. Written 2026-06-11 after reviewing Tasks 1–5
> and looking ahead into Tasks 6–8. Tasks 1–5 are committed; 24/24 pure-helper tests pass.

## Environment facts (verified 2026-06-11)

- Deps live in **`.venv` (Python 3.14.5)**: fastapi 0.136.3, skyfield 1.54, uvicorn 0.49.0,
  httpx 0.28.1, numpy, pytest. **System `python` lacks them** — the 24 passing tests only
  worked because they touch pure helpers. **Run all Task 6+ tests with `.venv/bin/python -m pytest`.**
- **`pandas` is NOT installed** and NOT in `requirements.txt`. skyfield needs it for
  `hipparcos.load_dataframe` and every dataframe op in Task 5. → confirmed gap (B1 below).
- **Docker is NOT installed** on this machine. Task 8 cannot run here as written (B2 below).
- `load.timescale()` works offline in the venv (builtin data). So `app/main.py`'s
  module-level `ts = load.timescale()` is fine.
- skyfield 1.54 has all APIs Task 5 uses (`almanac.risings_and_settings`, `find_maxima`,
  `ecliptic_J2000_frame`, `Star.from_dataframe`). requirements pins `>=1.49`, so OK.

---

## Blockers — fix before resuming Task 6

- [x] **B1. Add `pandas` to `requirements.txt`.** Done — `pandas>=2.2` added, installed in `.venv`.
- [x] **B2. Task 8 Docker strategy.** Docker is installed on this machine. Build + smoke test completed 2026-06-13.
- [x] **B3. Local skyfield data dir.** Downloaded `de421.bsp` (17 MB) and `hip_main.dat` (51 MB) to `/tmp/skyfield-data` for local runs. Container bakes both files at build time via `--network=host`.

## Task 6 (FastAPI app) — corrections to the plan as written

- [x] **T6.1. Fix mock binding.** `main.py` uses `from .astronomy import get_moon_data, …`,
  binding the names into `app.main` at import. `test_sky_api_success` patches
  `app.astronomy.*`, which then has no effect — so the **real, date-seeded `pick_mythology`
  runs** and `data["mythology"]["constellation"] == "Orion"` passes only by chance of today's
  hash. Fix: in `main.py` do `from . import astronomy, skymap` and call
  `astronomy.pick_mythology(...)` etc., **or** patch `app.main.*` in the tests. Pick one and
  apply it consistently.
- [ ] **T6.2. Static-file test ordering.** `test_static_css_served` / `test_static_js_served`
  need files created in Task 7. Either create the static files as part of Task 6, or mark
  those two tests to run after Task 7. Don't leave them red.
- [ ] **T6.3. Run with the venv:** `.venv/bin/python -m pytest tests/test_main.py -v`.

## Task 7 (frontend) — corrections

- [ ] **T7.1. Fix runic header typo in `app.js`.** `renderMythology` sets the header to
  `'ᛚᛖᛖᛖᛚ : '` (malformed). It should be `'ᛚᛖᚷᛖᚾᛞ : '` (LEGEND) to match `index.html`
  and the spec layout.
- [ ] **T7.2. After Task 7, full suite green:** `.venv/bin/python -m pytest -v` including the
  two static-file tests.

## Decision needed (spec deviation)

- [ ] **D1. Constellation visibility time.** Design spec §151 says "at local midnight";
  `get_visible_constellations` uses `ts.now()`. **Recommend keeping `now`** (consistent with
  the live sky map, more useful) — just confirm it's intentional and note it in the spec.

## Housekeeping (any time)

- [ ] **H1. Untrack stray brainstorm artifacts.** `.superpowers/brainstorm/*/state/server.{log,pid}`
  are committed; `.superpowers/` isn't gitignored. `git rm -r --cached .superpowers/` and add
  `.superpowers/` to `.gitignore`.

## Optional / defer

- [ ] **O1. Vectorize `get_visible_constellations`.** It does ~100 single-star skyfield
  observations in a nested loop and re-calls `observer.at(t)` per star. Hoist `observer.at(t)`
  and/or batch like `get_skymap_stars`. Perf only, not correctness.

---

## Resume order

1. B1 (pandas) + H1 (cleanup) — quick, unblock everything.
2. Decide D1 and B2 (Docker strategy).
3. Task 6 with T6.1 / T6.2 fixes folded in (don't transcribe the plan verbatim).
4. Task 7 with T7.1 fix.
5. Task 8 per the B2 decision (Docker elsewhere, or local uvicorn smoke test).
6. Final code review + `superpowers:finishing-a-development-branch`.
