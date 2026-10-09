FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    RACKET_GO_DATA_DIR=/app/data

WORKDIR /app

COPY pyproject.toml uv.lock ./
# Optional trusted CA bundle for builders behind an HTTPS inspection proxy.
# BuildKit keeps this file out of the final image and its layers.
RUN --mount=type=secret,id=build_ca_bundle \
    if [ -f /run/secrets/build_ca_bundle ]; then export SSL_CERT_FILE=/run/secrets/build_ca_bundle; fi \
    && uv sync --system-certs --frozen --no-dev --no-install-project

RUN useradd --system --uid 10001 --create-home racketgo \
    && mkdir -p /app/data \
    && chown racketgo:racketgo /app/data

COPY --chown=racketgo:racketgo app.py catalog.py security.py styles.css ./
COPY --chown=racketgo:racketgo assets/ ./assets/
COPY --chown=racketgo:racketgo .streamlit/config.toml ./.streamlit/config.toml

USER racketgo

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4)"]

CMD [".venv/bin/streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
