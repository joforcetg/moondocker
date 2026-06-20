FROM python:3.12.11-slim
LABEL org.opencontainers.image.source="https://github.com/joforcetg/moondocker" \
      org.opencontainers.image.description="Tonight's moon phase and night sky map" \
      org.opencontainers.image.licenses="MIT"
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

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

RUN useradd -r -u 1001 appuser && chown -R appuser:appuser /skyfield-data
USER appuser

ENV LAT="" LON="" PORT=7432 SKYFIELD_DATA=/skyfield-data
EXPOSE 7432

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
