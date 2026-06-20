# Backend, Docker & Docs Design — 2026-06-20

## Goal

Make moondocker production-ready for VPS self-hosting and open-source publication:
- Docker image hardened and published to GHCR (multi-arch)
- CI/CD via GitHub Actions
- docker-compose.yml VPS-ready
- README accurate and simple
- CONTRIBUTING.md + MIT LICENSE

---

## 1. Dockerfile hardening

**Changes:**
- Pin base image to `python:3.12.11-slim` (minor version lock, prevents surprise upgrades)
- Install `curl` (needed for HEALTHCHECK) before copying app code
- Create non-root user `appuser` (uid 1001), switch to it before CMD
- Add `HEALTHCHECK` instruction hitting `/health`
- Update `.dockerignore` to exclude `.venv/`, `tests/`, `docs/`, `*.md`, `*.tgz`, `ex_fonts/`

**Result:**
```dockerfile
FROM python:3.12.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download skyfield data at build time (network required during build)
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

---

## 2. FastAPI `/health` endpoint

Add to `app/main.py`:

```python
@app.get("/health")
def health():
    return {"status": "ok"}
```

- Pure liveness check — no skyfield, no computation
- Used by Docker HEALTHCHECK and reverse proxy upstreams
- No test needed (no logic)

---

## 3. GitHub Actions CI/CD

### Existing: `.github/workflows/test.yml`
No changes. Runs pytest on push/PR to main.

### New: `.github/workflows/docker-publish.yml`

**Triggers:** push to `main`, push of tags matching `v*.*.*`

**Steps:**
1. `actions/checkout@v4`
2. `docker/setup-qemu-action@v3` — ARM64 emulation
3. `docker/setup-buildx-action@v3`
4. `docker/login-action@v3` — GHCR via `GITHUB_TOKEN` (no extra secrets)
5. `docker/metadata-action@v5` — generates tags:
   - `:latest` on every `main` push
   - `:sha-<short>` for traceability
   - `:1.2.3`, `:1.2`, `:1` on `v1.2.3` tag push
6. `docker/build-push-action@v6` — `platforms: linux/amd64,linux/arm64`, push on `main` only (not PRs)

**Expected build time:** 8–12 min (arm64 emulation via QEMU).

**Permissions required in workflow:**
```yaml
permissions:
  contents: read
  packages: write
```

---

## 4. docker-compose.yml (VPS-ready)

Replace current file:

```yaml
services:
  moondocker:
    image: ghcr.io/joforcetg/moondocker:latest
    restart: unless-stopped
    ports:
      - "7432:7432"
    environment:
      LAT: ""
      LON: ""
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7432/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s
```

- Uses published image by default
- Build-from-source variant documented in README only

---

## 5. README updates

Targeted additions to existing README (no full rewrite):

- **Badges** at top: CI status + GHCR image badge
- **VPS deploy section**: `docker compose up -d`, Caddy reverse proxy example
- **Updating section**: `docker compose pull && docker compose up -d`

README stays simple — no security section, no elaborate docs. The app has no secrets, no user data, no auth.

---

## 6. CONTRIBUTING.md + LICENSE

**LICENSE:** MIT

**CONTRIBUTING.md** covers:
- Clone + `.venv` setup
- `pip install -r requirements-dev.txt`
- Run tests: `.venv/bin/python -m pytest -v`
- Run app locally (with `SKYFIELD_DATA`)
- PR guidelines: small commits, tests must pass, no new deps without discussion
- Mocking note: patch `app.main.*` not source module

~40 lines, no templates, no issue forms.

---

## Files changed

| File | Action |
|------|--------|
| `Dockerfile` | Modify |
| `.dockerignore` | Modify |
| `app/main.py` | Modify (add `/health`) |
| `.github/workflows/docker-publish.yml` | Create |
| `docker-compose.yml` | Modify |
| `README.md` | Modify (targeted additions) |
| `CONTRIBUTING.md` | Create |
| `LICENSE` | Create |
