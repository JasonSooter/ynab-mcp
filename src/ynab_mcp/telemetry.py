"""Login events, logged to stdout.

anki-mcp and obsidian-mcp ship these over OTLP to Grafana; this server logs
them only, so `docker logs ynab-mcp` is where failed logins show up. The
submitted password and code are never recorded.
"""

from __future__ import annotations

import logging

log = logging.getLogger("ynab_mcp.login")


def record_login(*, success: bool, client_ip: str, reason: str | None = None) -> None:
    if success:
        log.info("login ok from %s", client_ip)
    else:
        log.warning("login failed from %s (%s)", client_ip, reason)
