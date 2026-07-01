# Session handoff: UI redesign, scroll fix, dependency updates

Date: 2026-07-01
Branch of record: `main` (all shipped work is already merged; this doc is the only thing on `docs/session-handoff`)

## What changed

### Horror/witch UI redesign (`7f5855f`)
The frontend was a bare greyscale grimoire that read as empty. It now has a fuller
occult look, done entirely in CSS with no new images or JS libraries.

- Blood accent (`--blood: #8a1c1c`) used sparingly: active constellation glow, rune
  labels, the myth-title rule, and the drop cap.
- Candle-flicker glow, CRT scanlines over heavier grain, aged-paper panel fills, etched
  panel frames with corner rune sigils, a faint sigil watermark behind the star map, and
  a blood drop cap on the loaded myth text.
- Fonts: dropped the UnifrakturCook blackletter (hard to read, worse small on phones) for
  Cinzel, self-hosted as woff2 from `@fontsource/cinzel`. Titles are uppercase Cinzel.
  Turned on `-webkit-font-smoothing` and `text-rendering: optimizeLegibility`, and raised
  the myth text from dim grey to bone for contrast.
- Responsive: added `viewport-fit=cover` so the iOS safe-area rules actually apply, and
  dropped the `vh`-based caps on the sky map that shrank it in landscape.

### Phone scroll fix (`1bc7c9f`)
Tapping a constellation scrolled to the legend before its text had loaded, so it landed
in the wrong place. The scroll now fires after the myth text is in the DOM and targets the
loaded header. The real culprit was a page-wide `scroll-behavior: smooth`: it made every
programmatic scroll animate, so an in-flight scroll (phone momentum, or the test resetting
to the top) collided with the `scrollIntoView` and both stalled halfway. Removed the global
rule and let `app.js` drive the one scroll it wants with an explicit smooth behavior.

### Wide-screen layout fix (`14f6197`)
On wide screens the sky panel kept its square-map height while the column beside it ran
longer with a selected myth, leaving a dead gap. The sky panel now stretches to the column
height with the map centered, so both columns end level.

### UI check script (`scripts/ui_check.py`)
A standalone Playwright loop test, using the Playwright already in the venv (no
pytest-playwright, no fixtures). It boots the app once, or attaches to a running server via
`--url` for fast edit-and-rerun loops, and runs 25 checks across five widths: layout
overflow and grid reflow, fonts loaded with the blackletter gone, myth text contrast, the
blood drop cap, candle flicker, panel frames, and the scroll actually landing on the loaded
myth. Screenshots go to `ui-shots/` (gitignored).

```
.venv/bin/python scripts/ui_check.py
.venv/bin/python scripts/ui_check.py --url http://127.0.0.1:7432   # reuse a running server
```

### Base image CVE fix (`7ca61cf`, Dependabot #17)
CI/CD went red on a Trivy scan: `libssh2` picked up three fixable CVEs (one CRITICAL,
`CVE-2026-55200`, plus two HIGH), disclosed mid-session. The Dockerfile already runs
`apt-get upgrade`, but that layer is Docker-cached and only rebuilds when the base image
digest changes. Merging the Dependabot base bump (`44dd044` to `b877e50`) busted the cache,
so the upgrade pulled the patched `libssh2 1.11.1-1+deb13u1`. Scan is green.

### Dependency updates (Dependabot)
Merged: fastapi (#18), pytest (#19), pip-audit (#20), gitleaks-action (#21),
skyfield >=1.54 (#22). `main` is green at `c5eca75`.

## Open items

- **PR #23 (hadolint-action 3.1.0 to 3.3.0)** is still open. It edits a workflow file, and
  the token in use here lacks the `workflow` scope, so it can't be merged from the CLI.
  Merge it in the GitHub UI, or let Dependabot do it. It is mergeable and green.
- **PR #13 (python 3.12.11 to 3.14.6)** is obsolete now that #17 put us on 3.14.6. Close it.
- **CI has no concurrency guard.** Merging five PRs in a row spawned five overlapping
  build-and-push jobs that fought over the buildx cache and the `:latest` tag, so a couple
  failed spuriously. Reruns cleared them. Adding a `concurrency:` block to the workflow would
  stop this.
- **Desktop sky map looks airy** in the stretched panel (map centered in a taller frame).
  If that reads as too empty, the alternative is capping the sky height instead of stretching.
- **Myth artwork** comes back null when the app runs without network access to
  `upload.wikimedia.org`. It is UI-only and degrades gracefully.

## How to verify

```
.venv/bin/python -m pytest -q          # 77 backend tests
.venv/bin/python scripts/ui_check.py   # 25 browser checks, screenshots in ui-shots/
```
