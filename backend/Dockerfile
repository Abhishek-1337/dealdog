# Build the dependency set in a throwaway stage so the runtime image carries no
# pip cache, no build tooling and no wheels — only the installed venv.
FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /src

# `pip install .` builds the `app` package, so the source has to be present at
# install time — there is no requirements.txt to copy on its own.
COPY pyproject.toml ./
COPY app ./app

RUN python -m venv /opt/venv && /opt/venv/bin/pip install .


FROM python:3.11-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Non-root: the container only ever reads its own code and talks to Neon and
# OpenAI over the network, so it never needs write access to anything.
RUN useradd --create-home --uid 10001 dealdog

WORKDIR /srv

COPY --from=builder /opt/venv /opt/venv
# The source is copied as well as installed. `Settings` reads `env_file=".env"`
# relative to the working directory, so /srv is also where a mounted .env lands.
COPY app ./app

USER dealdog

EXPOSE 8000

# No curl in the slim image, so the check runs through the interpreter that is
# already here. Hits the real router prefix — health is at /api/health.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"

# --proxy-headers so client IPs and the request scheme survive the reverse proxy
# that terminates TLS in front of this container.
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
