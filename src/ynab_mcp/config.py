"""Environment-driven configuration.

Secrets (the YNAB token, the login password and TOTP secret) come from the
environment only, never from a file in the repo.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# The login password is the outer wall on a public endpoint. TOTP is the second
# factor, but a weak password makes the pair only as strong as six digits.
MIN_PASSWORD_LENGTH = 12


class ConfigError(RuntimeError):
    """Raised at startup for a config problem that must stop the process."""


@dataclass(frozen=True)
class Config:
    login_password: str
    totp_secret: str
    host: str
    port: int
    public_url: str
    state_dir: Path

    @property
    def oauth_db_path(self) -> Path:
        # Clients, tokens and the last TOTP counter. Must persist: losing it
        # means re-adding the connector on every device.
        return self.state_dir / "oauth.db"

    @property
    def cache_db_path(self) -> Path:
        # Upstream mcp-ynab's delta-sync cache. Losing it only costs a full
        # re-fetch from the YNAB API.
        return self.state_dir / "cache.db"


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or default


def load() -> Config:
    # Fail closed: the login page is the only thing between the public internet
    # and a token that can edit the budget, so a missing factor stops startup
    # rather than serving unauthenticated.
    missing = [
        name
        for name in ("YNAB_API_KEY", "YNAB_MCP_LOGIN_PASSWORD", "YNAB_MCP_TOTP_SECRET")
        if not _env(name)
    ]
    if missing:
        raise ConfigError(f"required but unset: {', '.join(missing)}")

    login_password = _env("YNAB_MCP_LOGIN_PASSWORD")
    assert login_password is not None
    if len(login_password) < MIN_PASSWORD_LENGTH:
        raise ConfigError(
            f"YNAB_MCP_LOGIN_PASSWORD is only {len(login_password)} characters; "
            f"use at least {MIN_PASSWORD_LENGTH}"
        )

    port_raw = _env("YNAB_MCP_PORT", "8790")
    try:
        port = int(port_raw or "8790")
    except ValueError:
        raise ConfigError(f"YNAB_MCP_PORT is not a number: {port_raw!r}") from None

    return Config(
        login_password=login_password,
        totp_secret=_env("YNAB_MCP_TOTP_SECRET") or "",
        host=_env("YNAB_MCP_HOST", "0.0.0.0") or "0.0.0.0",
        port=port,
        # Only feeds OAuth discovery metadata, so a localhost default is
        # harmless for local runs; on the box it is the Funnel URL.
        public_url=_env("YNAB_MCP_PUBLIC_URL") or f"http://localhost:{port}",
        state_dir=Path(_env("YNAB_MCP_STATE_DIR", "/data") or "/data"),
    )
