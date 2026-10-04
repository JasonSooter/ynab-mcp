# YNAB MCP over Streamable HTTP. The tools are upstream mcp-ynab's, installed
# from PyPI at the version uv.lock pins; this image adds the HTTP transport and
# the password + TOTP OAuth login in front of them.
# Pinned by digest; Renovate proposes digest updates weekly (renovate.json).
# 3.13, not 3.12 like anki-mcp and obsidian-mcp: upstream requires it.
FROM python:3.13-slim@sha256:3dd7cc108ec1493442514f5c2a871af6af0ec31d768ff6e378a93340c3b3db5f

# Pinned by digest: a moving tag would silently change the builder.
COPY --from=ghcr.io/astral-sh/uv:0.12.23@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21 /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    YNAB_MCP_STATE_DIR=/data \
    YNAB_MCP_PORT=8790

WORKDIR /app
# Dependencies come from uv.lock, so the image ships exactly the versions CI
# tested -- not whatever resolves on the day it is built. The project itself is
# installed afterwards with --no-deps for the same reason.
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv export --frozen --no-dev --no-emit-project -o /tmp/requirements.txt \
 && uv pip install --system --no-cache -r /tmp/requirements.txt \
 && uv pip install --system --no-cache --no-deps . \
 && rm /tmp/requirements.txt

# /data holds oauth.db (connector registrations and tokens) and upstream's
# cache.db. It is bind-mounted at run time; creating it keeps the image
# runnable standalone for a smoke test.
RUN mkdir -p /data && chown 1000:1000 /data
USER 1000:1000
# Run from /data rather than /app: upstream's top-level package is named `src`,
# and /app/src (this project's source) would otherwise sit first on sys.path.
WORKDIR /data

# Stamps the commit this image was built from, so a running container can say
# what it contains. CI passes the commit SHA; a local build leaves it "unknown".
# Declared late so changing it does not invalidate the dependency layers above.
ARG GIT_REVISION=unknown
LABEL org.opencontainers.image.revision="$GIT_REVISION"
LABEL org.opencontainers.image.source="https://github.com/JasonSooter/ynab-mcp"
LABEL org.opencontainers.image.title="ynab-mcp"
LABEL org.opencontainers.image.licenses="AGPL-3.0-only"

EXPOSE 8790

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8790/healthz', timeout=4).status==200 else 1)"

CMD ["python", "-m", "ynab_mcp"]
