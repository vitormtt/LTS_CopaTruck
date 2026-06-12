# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1: base — Python runtime + scientific dependencies.
# Shared foundation for the Streamlit app today and for a future REST API
# service (add a new stage `FROM base AS api` when the backend is split out).
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt ./

# libxrk has no wheels for every platform; the codebase degrades gracefully
# without it (AiM .xrk parsing is optional), so its failure must not break
# the image build.
RUN grep -v "^libxrk" requirements.txt > /tmp/requirements-core.txt \
    && pip install -r /tmp/requirements-core.txt \
    && (pip install "libxrk>=0.12.0" \
        || echo "WARNING: libxrk unavailable for this platform — .xrk parsing disabled") \
    && rm /tmp/requirements-core.txt

# ---------------------------------------------------------------------------
# Stage 2: app — Streamlit UI + simulation core.
# ---------------------------------------------------------------------------
FROM base AS app

COPY src/ src/
COPY data/ data/
COPY tracks/ tracks/

# Writable paths: JSON fallback storage, exported CSVs, persisted tracks.
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p data src/results tracks/custom \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=3)" || exit 1

CMD ["streamlit", "run", "src/visualization/interface.py", \
     "--server.address=0.0.0.0", "--server.port=8501", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
