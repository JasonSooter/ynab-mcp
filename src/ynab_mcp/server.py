"""Server assembly: upstream's tools behind our OAuth login."""

from __future__ import annotations

import os

from mcp.server.auth.settings import (
    AuthSettings,
    ClientRegistrationOptions,
    RevocationOptions,
)
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.tools.base import Tool
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from .auth import YNAB_SCOPE
from .config import Config
from .oauth.login import register_routes as register_login_routes
from .oauth.provider import YnabOAuthProvider
from .oauth.store import Store
from .oauth.totp import normalise_secret

INSTRUCTIONS = """\
Read and edit a YNAB budget (YNAB calls a budget a "plan").

Call list_plans first to find the plan_id every other tool takes. Amounts are in
milliunits: 1000 = 1.00 in the budget's currency, and outflows are negative.

Writes are real and immediate: create, update and delete tools change the
budget the family uses. Confirm with the user before any of them.
"""


def upstream_tools() -> list[Tool]:
    """The tools upstream mcp-ynab registers, as SDK Tool objects.

    Upstream builds its own MCPServer at import time and serves it over stdio.
    We keep its tools and replace the server around them, since auth is a
    constructor argument. Reading its tool manager is the one private access
    here; tests/test_server.py fails if an SDK or upstream bump breaks it.

    Imported here, not at module level: upstream reads its settings (the YNAB
    token, the cache path) the moment it is imported.
    """
    from src.server._shared import mcp as upstream  # noqa: PLC0415
    import src.server  # noqa: F401, PLC0415  (registers the tools on `upstream`)

    return upstream._tool_manager.list_tools()


def build(config: Config) -> tuple[MCPServer, Starlette]:
    os.environ.setdefault("CACHE_DB_PATH", str(config.cache_db_path))

    store = Store(config.oauth_db_path)
    oauth_provider = YnabOAuthProvider(store)
    auth_settings = AuthSettings(
        issuer_url=config.public_url,
        resource_server_url=config.public_url,
        required_scopes=[YNAB_SCOPE],
        # Claude registers itself when you add the connector; without dynamic
        # registration you would have to pre-provision a client id.
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=[YNAB_SCOPE],
            default_scopes=[YNAB_SCOPE],
        ),
        revocation_options=RevocationOptions(enabled=True),
    )

    mcp = MCPServer(
        name="ynab",
        title="YNAB",
        instructions=INSTRUCTIONS,
        auth_server_provider=oauth_provider,
        # Enabling auth here is what makes the SDK reject unauthenticated
        # requests before they ever reach a tool.
        auth=auth_settings,
        tools=upstream_tools(),
    )

    register_login_routes(
        mcp,
        oauth_provider,
        store,
        config.login_password,
        normalise_secret(config.totp_secret),
    )

    @mcp.custom_route("/healthz", methods=["GET"])
    async def healthz(request: Request) -> JSONResponse:
        """Liveness probe. Unauthenticated, public via Funnel, so contentless."""
        return JSONResponse({"status": "ok"})

    app = mcp.streamable_http_app(host=config.host)
    return mcp, app
