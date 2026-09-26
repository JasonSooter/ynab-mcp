from __future__ import annotations

import base64
import hashlib
import secrets
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from starlette.testclient import TestClient

import src.server as upstream_pkg
from ynab_mcp.config import Config, ConfigError, load
from ynab_mcp.oauth.totp import _code_for_counter, normalise_secret
from ynab_mcp.server import build, upstream_tools

TOTP_SECRET = "JBSWY3DPEHPK3PXP"  # RFC 6238 example key, not a real secret
PASSWORD = "correct horse battery staple"
REDIRECT = "http://localhost:9999/callback"


def config(tmp_path: Path) -> Config:
    return Config(
        login_password=PASSWORD,
        totp_secret=TOTP_SECRET,
        host="127.0.0.1",
        port=8790,
        public_url="http://localhost:8790",
        state_dir=tmp_path,
    )


@pytest.fixture
def client(tmp_path: Path):
    _, app = build(config(tmp_path))
    with TestClient(app, base_url="http://localhost:8790", follow_redirects=False) as c:
        yield c


# ---- the tool transplant: the one place we lean on SDK internals ----------


def test_every_upstream_tool_is_served() -> None:
    exported = set(upstream_pkg.__all__) - {"main"}
    served = {t.name for t in upstream_tools()}
    assert exported, "upstream's __all__ is empty; the tool list cannot be checked"
    assert exported <= served, f"missing: {sorted(exported - served)}"


# ---- config fails closed ----------------------------------------------------


def test_config_refuses_to_start_without_both_factors(monkeypatch) -> None:
    monkeypatch.setenv("YNAB_MCP_LOGIN_PASSWORD", PASSWORD)
    monkeypatch.delenv("YNAB_MCP_TOTP_SECRET", raising=False)
    with pytest.raises(ConfigError, match="YNAB_MCP_TOTP_SECRET"):
        load()


def test_config_rejects_a_short_password(monkeypatch) -> None:
    monkeypatch.setenv("YNAB_MCP_LOGIN_PASSWORD", "short")
    monkeypatch.setenv("YNAB_MCP_TOTP_SECRET", TOTP_SECRET)
    with pytest.raises(ConfigError, match="at least"):
        load()


# ---- HTTP surface -------------------------------------------------------------


def test_healthz_is_open(client: TestClient) -> None:
    assert client.get("/healthz").status_code == 200


def test_mcp_rejects_unauthenticated_requests(client: TestClient) -> None:
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert r.status_code == 401


def test_oauth_discovery_metadata(client: TestClient) -> None:
    r = client.get("/.well-known/oauth-authorization-server")
    assert r.status_code == 200
    assert r.json()["registration_endpoint"].endswith("/register")


def test_full_login_reaches_the_tools(client: TestClient) -> None:
    reg = client.post(
        "/register",
        json={
            "redirect_uris": [REDIRECT],
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
        },
    )
    assert reg.status_code == 201, reg.text
    client_id = reg.json()["client_id"]

    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    auth = client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": "s1",
            "scope": "ynab",
        },
    )
    assert auth.status_code in (302, 307), auth.text
    login_url = auth.headers["location"]
    assert "/login?login_id=" in login_url

    code_now = _code_for_counter(normalise_secret(TOTP_SECRET), int(time.time() // 30))
    wrong = client.post(login_url, data={"password": "not the password", "totp": code_now})
    assert "Incorrect password or code." in wrong.text

    ok = client.post(login_url, data={"password": PASSWORD, "totp": code_now})
    assert ok.status_code in (302, 303), ok.text
    code = parse_qs(urlparse(ok.headers["location"]).query)["code"][0]

    tok = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT,
            "client_id": client_id,
            "code_verifier": verifier,
        },
    )
    assert tok.status_code == 200, tok.text
    headers = {
        "Authorization": f"Bearer {tok.json()['access_token']}",
        "Accept": "application/json, text/event-stream",
    }

    init = client.post(
        "/mcp",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0"},
            },
        },
    )
    assert init.status_code == 200, init.text
    session = init.headers.get("mcp-session-id")
    if session:
        headers["mcp-session-id"] = session
    client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    listed = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert listed.status_code == 200, listed.text
    assert '"list_plans"' in listed.text
