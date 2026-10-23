FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as an unprivileged user. It owns storage/ because the app writes
# invoice PDFs there; a new named volume mounted on it copies this ownership.
RUN useradd --create-home app && mkdir -p storage/invoices && chown -R app storage
USER app

# Liveness only: "/" doesn't touch the database, so a short database outage
# doesn't mark the container unhealthy. Uses Python because slim has no curl.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/', timeout=3)"

# Migrations are not run here: docker-compose.yml runs them once, in the
# migrate service, before this starts (several replicas would otherwise race
# to migrate at startup). Exec form so uvicorn gets docker stop's signal
# directly and shuts down cleanly.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
