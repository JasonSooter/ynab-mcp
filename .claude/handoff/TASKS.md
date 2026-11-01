# Task register — durable, permanent record

**Why this file exists:** the Claude Code session task list is **not file-backed**. A task
created with `TaskCreate` and never written here is gone at `/clear` or session end. This
file is the durable copy. Rehydrate the session list from it; never the reverse.

Started 2026-11-01 with tasks moved from the
[home-media-server](https://github.com/JasonSooter/home-media-server) register, which
deploys this server; each row names its old ID there. Code work for this server is tracked
here; hosting it (compose, Tailscale, secrets on the box) stays in home-media-server.

**Next ID: T-003**

---

## 🎯 Priority

None set. Pick from the register.

---

## Register

| ID | Status | Subject | Detail |
|----|--------|---------|--------|
| T-001 | open | Ship login events to Grafana like anki-mcp and obsidian-mcp | `telemetry.py` only logs `record_login` locally (`logging`, visible in `docker logs`). anki-mcp and obsidian-mcp send OTLP to Loki and have dashboards and alerts. Port obsidian-mcp's `telemetry.py`, add the OTLP env vars to the deployment's secrets, and consider a failed-login alert: this endpoint can edit the budget, so failed logins matter. No work started; checked 2026-11-01. (Was home-media-server T-059.) |
| T-002 | open | Decide `AuthSettings.validate_token_resource` before mcp SDK 3.0 | Every server logs `MCPDeprecationWarning: AuthSettings.validate_token_resource is not set`. In mcp SDK 3.0 it defaults to True whenever `resource_server_url` is set, and our providers don't record the token's `resource`, so a silent SDK bump could reject every token. Decide in all three repos together (anki-mcp, obsidian-mcp, ynab-mcp; the OAuth code is shared). No work started; checked 2026-11-01: not set anywhere. (Was home-media-server T-060.) |

---

## 📌 Standing facts that save re-derivation

- The OAuth code is shared by anki-mcp, obsidian-mcp and ynab-mcp: fix bugs in all three.

---

## ⚠️ False premises and method traps

- None recorded yet.

---

## 🗓️ Time-bound checks

- None.
