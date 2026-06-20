# Backend, Docker & Docs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the Docker image, publish it to GHCR via GitHub Actions (multi-arch), and add open-source docs so moondocker is VPS-ready and contributor-friendly.

**Architecture:** Eight files touched in dependency order — API endpoint first (needed by HEALTHCHECK), then Dockerfile (consumes `/health`), then compose and CI (consume Dockerfile), then docs (reference everything). Each task is independently testable.

**Tech Stack:** Python 3.12, FastAPI, Docker Buildx, GitHub Actions, GHCR (ghcr.io)

## Global Constraints

- All Python commands use `.venv/bin/python` — system Python lacks deps
- Run tests with `.venv/bin/python -m pytest -v`
- Never touch `.env` or secrets
- Patch targets are `app.main.*`, not source modules (see CLAUDE.md)
- Base image: `python:3.12.11-slim`
- GHCR image: `ghcr.io/joforcetg/moondocker`
- Non-root user in container: `appuser` (uid 1001)

---

### Task 1: Add `/health` endpoint

**Files:**
- Modify: `app/main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Produces: `GET /health → 200 {"status": "ok"}`

- [ ] **Step 1: Write the failing test**

Open `tests/test_main.py` and add at the end:

```python
def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m pytest tests/test_main.py::test_health -v
```

Expected: `FAILED` — `404 Not Found`

- [ ] **Step 3: Add the endpoint to `app/main.py`**

Find the line where `app = FastAPI(...)` is defined (or just after the imports). Add before the first `@app.get` route:

```python
@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/bin/python -m pytest tests/test_main.py::test_health -v
```

Expected: `PASSED`

- [ ] **Step 5: Run full test suite**

```bash
.venv/bin/python -m pytest -v
```

Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add app/main.py tests/test_main.py
git commit -m "feat: add /health liveness endpoint"
```

---

### Task 2: Harden Dockerfile and .dockerignore

**Files:**
- Modify: `Dockerfile`
- Modify: `.dockerignore`

**Interfaces:**
- Consumes: `GET /health` from Task 1 (used in HEALTHCHECK)
- Produces: hardened image with non-root user, curl, pinned base, HEALTHCHECK

- [ ] **Step 1: Replace `Dockerfile` contents**

```dockerfile
FROM python:3.12.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download skyfield data at build time so the container runs offline.
# Uses python -c (not a heredoc) so it works with both the legacy builder and BuildKit.
# hip_main.dat is fetched via hipparcos.URL — load.open(filename) only opens local files.
# If your build environment lacks outbound network, pass --network=host to docker build.
RUN python -c "\
from skyfield.api import Loader; \
from skyfield.data import hipparcos; \
load = Loader('/skyfield-data'); \
load('de421.bsp'); \
hipparcos.load_dataframe(load.open(hipparcos.URL))" && \
    test -s /skyfield-data/de421.bsp && \
    test -s /skyfield-data/hip_main.dat

COPY data/ ./data/
COPY app/ ./app/

RUN useradd -r -u 1001 appuser
USER appuser

ENV LAT="" LON="" PORT=7432 SKYFIELD_DATA=/skyfield-data
EXPOSE 7432

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```

- [ ] **Step 2: Replace `.dockerignore` contents**

```
.git
.venv/
venv/
tests/
docs/
ex_fonts/
.superpowers/
.pytest_cache/
.aider*
*.md
*.tgz
**/__pycache__
**/*.pyc
*.env
```

- [ ] **Step 3: Verify build locally**

```bash
docker build -t moondocker-test .
```

Expected: build completes successfully (skyfield data downloaded, `test -s` checks pass)

- [ ] **Step 4: Verify non-root user**

```bash
docker run --rm moondocker-test whoami
```

Expected: `appuser`

- [ ] **Step 5: Verify HEALTHCHECK is registered**

```bash
docker inspect moondocker-test | grep -A5 Health
```

Expected: shows `Test`, `Interval`, `Timeout` fields

- [ ] **Step 6: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "feat(docker): pin base image, non-root user, HEALTHCHECK, tighter dockerignore"
```

---

### Task 3: VPS-ready docker-compose.yml

**Files:**
- Modify: `docker-compose.yml`

**Interfaces:**
- Consumes: `GET /health` from Task 1, HEALTHCHECK from Task 2

- [ ] **Step 1: Replace `docker-compose.yml` contents**

```yaml
services:
  moondocker:
    image: ghcr.io/joforcetg/moondocker:latest
    restart: unless-stopped
    ports:
      - "7432:7432"
    environment:
      LAT: ""   # optional fallback latitude; leave blank to use browser geolocation
      LON: ""   # optional fallback longitude
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7432/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s
```

- [ ] **Step 2: Validate compose file**

```bash
docker compose config
```

Expected: prints resolved YAML with no errors

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat(compose): VPS-ready — restart policy, healthcheck, pull from GHCR"
```

---

### Task 4: GitHub Actions multi-arch publish workflow

**Files:**
- Create: `.github/workflows/docker-publish.yml`

**Interfaces:**
- Consumes: `Dockerfile` from Task 2
- Produces: `ghcr.io/joforcetg/moondocker:latest` + `:sha-<hash>` + semver tags on `v*.*.*`

- [ ] **Step 1: Create `.github/workflows/docker-publish.yml`**

```yaml
name: Publish Docker image

on:
  push:
    branches: [main]
    tags: ["v*.*.*"]

permissions:
  contents: read
  packages: write

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=raw,value=latest,enable={{is_default_branch}}
            type=sha,prefix=sha-,format=short
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=semver,pattern={{major}}

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: ${{ github.event_name == 'push' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

- [ ] **Step 2: Verify YAML is valid**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/docker-publish.yml'))" && echo "YAML OK"
```

Expected: `YAML OK`

- [ ] **Step 3: Commit and push**

```bash
git add .github/workflows/docker-publish.yml
git commit -m "feat(ci): multi-arch Docker build and push to GHCR on main push"
git push
```

- [ ] **Step 4: Verify workflow runs**

Go to `https://github.com/joforcetg/moondocker/actions` — confirm `Publish Docker image` workflow appears and passes. First run ~8–12 min (arm64 QEMU emulation).

---

### Task 5: README targeted additions

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add badges after the title line**

After `# moondocker` and before the screenshot line, add:

```markdown
[![CI](https://github.com/joforcetg/moondocker/actions/workflows/test.yml/badge.svg)](https://github.com/joforcetg/moondocker/actions/workflows/test.yml)
[![Docker](https://ghcr-badge.egpl.dev/joforcetg/moondocker/size)](https://github.com/joforcetg/moondocker/pkgs/container/moondocker)
```

- [ ] **Step 2: Add VPS deploy section**

After the `---` that follows the `docker-compose` section, add a new section:

```markdown
## VPS deploy

```bash
# pull and start in background
docker compose up -d
```

To put it behind a domain with automatic HTTPS, add a [Caddyfile](https://caddyserver.com/docs/quick-starts/reverse-proxy):

```
moondocker.example.com {
    reverse_proxy localhost:7432
}
```

Then `caddy reload`.

---

## Updating

```bash
docker compose pull
docker compose up -d
```

---
```

- [ ] **Step 3: Review the full README visually**

```bash
cat README.md
```

Check: badges at top, VPS section present, Updating section present, no broken markdown.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(readme): add CI/Docker badges, VPS deploy and updating sections"
```

---

### Task 6: CONTRIBUTING.md + LICENSE

**Files:**
- Create: `CONTRIBUTING.md`
- Create: `LICENSE`

- [ ] **Step 1: Create `LICENSE`**

```
MIT License

Copyright (c) 2026 joforcetg

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Create `CONTRIBUTING.md`**

```markdown
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
```

- [ ] **Step 3: Run tests to confirm nothing broken**

```bash
.venv/bin/python -m pytest -v
```

Expected: all tests pass

- [ ] **Step 4: Commit**

```bash
git add LICENSE CONTRIBUTING.md
git commit -m "docs: add MIT license and contributing guide"
```
