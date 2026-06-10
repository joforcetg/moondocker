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
