"""Entrypoint: validate config, then serve. A bad config exits non-zero."""

from __future__ import annotations

import logging
import sys

import uvicorn

from .config import ConfigError, load
from .oauth.totp import InvalidTOTPSecret
from .server import build

log = logging.getLogger("ynab_mcp")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    try:
        config = load()
        config.state_dir.mkdir(parents=True, exist_ok=True)
        _, app = build(config)
    except (ConfigError, InvalidTOTPSecret) as exc:
        log.error("configuration error: %s", exc)
        return 2
    except OSError as exc:
        log.error("state directory %s is not usable: %s", config.state_dir, exc)
        return 4

    log.info("serving MCP on http://%s:%s/mcp (auth: oauth)", config.host, config.port)
    uvicorn.run(app, host=config.host, port=config.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
