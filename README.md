# ynab-mcp

Your [YNAB](https://www.ynab.com) budget as MCP tools, reachable from every
Claude client (Claude Code, Desktop, claude.ai and mobile), behind a password +
TOTP login.

The tools are [`mcp-ynab`](https://github.com/pragprogrammer/mcp-ynab) by
Michael Green, installed unchanged from PyPI at the version `uv.lock` pins.
Upstream serves them over stdio only, which no phone or browser can reach. This
project adds the two things a hosted server needs:

- **Streamable HTTP** at `/mcp`, served by uvicorn.
- **OAuth 2.1 with a password + TOTP login**, which claude.ai and the mobile apps
  need to add it as a connector. The token behind it can edit the budget, so the
  server refuses to start without both factors. The OAuth code is shared with
  [anki-mcp](https://github.com/JasonSooter/anki-mcp) and
  [obsidian-mcp](https://github.com/JasonSooter/obsidian-mcp).

## How it reuses upstream

Upstream builds an `MCPServer` and registers its tools on it at import time.
`src/ynab_mcp/server.py` imports that, takes its tool list and passes it to a new
`MCPServer` that has auth configured. No tool code is copied or changed. Reading
the tool list touches one private SDK attribute; `tests/test_server.py` checks
that every tool upstream exports is still served, so a breaking bump fails CI.

## Run it

```bash
docker run -d --name ynab-mcp \
  --env-file secrets.env \
  -e YNAB_MCP_PUBLIC_URL=https://ynab.example.ts.net \
  -v "$PWD/data:/data" \
  -p 127.0.0.1:8790:8790 \
  ghcr.io/jasonsooter/ynab-mcp:main
```

| variable | default | meaning |
|---|---|---|
| `YNAB_API_KEY` | required | YNAB personal access token |
| `YNAB_MCP_LOGIN_PASSWORD` | required | login password, ≥ 12 characters |
| `YNAB_MCP_TOTP_SECRET` | required | base32 TOTP setup key |
| `YNAB_MCP_PUBLIC_URL` | `http://localhost:8790` | the public HTTPS URL; feeds OAuth discovery |
| `YNAB_MCP_STATE_DIR` | `/data` | holds `oauth.db` (connector logins) and `cache.db` (upstream's cache) |
| `YNAB_MCP_PORT` | `8790` | listen port |

`/data` must persist. Without it, every device has to add the connector again
after a restart. Put the endpoint behind HTTPS (e.g. Tailscale Funnel) before
adding it to Claude, and add it as `https://<host>/mcp`.

## Develop

```bash
uv sync
uv run pytest
```

CI runs the tests, then builds the image for amd64 and arm64, and pushes it to
`ghcr.io/jasonsooter/ynab-mcp` on `main` (tags `main` and `sha-<commit>`).

## License

AGPL-3.0-only, the same as upstream mcp-ynab, whose code the image contains.
