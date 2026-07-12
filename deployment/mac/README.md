# mac

The MacBook Pro (M4 Max) is a tracked host in this repo, but unlike `tenzing`/`tyr`/`gliese`
there's no automated CD path here — no self-hosted runner reaches a laptop that sleeps and
roams, and the load-bearing pieces (LM Studio, Obsidian community plugins) are GUI apps with
no headless install mechanism. What's here is what's actually codifiable: launch agent config
and MCP client wiring, applied by hand.

## Prerequisites (manual, one-time)

1. [LM Studio](https://lmstudio.ai/) installed, with the CLI bootstrapped
   (`Cmd+Shift+P` → "Bootstrap CLI" in-app, or `~/.lmstudio/bin/lms bootstrap`) so `lms` is on
   `PATH`. Load whatever model you want resident (see `deployment/containers/litellm/litellm-config.yaml`
   on gliese for the model name the proxy expects — keep them in sync).
2. [Obsidian](https://obsidian.md/) with the vault opened, plus the community plugins
   **Copilot** and **Smart Connections** installed and enabled (Settings → Community plugins →
   Browse). Plugin *install* is manual; plugin *settings* are documented in
   `obsidian/plugin-settings.md`.
3. [Tailscale](https://tailscale.com/download/mac) installed and joined to the same tailnet as
   `tyr`/`gliese`/`tenzing`. This is what lets:
   - the `litellm` proxy on `gliese` reach LM Studio here (`http://<mac-tailscale-ip>:1234/v1`)
   - Obsidian Copilot here reach `litellm.gliese.{{ oci_parent_host }}`
   Get the IP with `tailscale ip -4` and put it in gliese's `secrets.yml` as
   `mac_tailscale_ip` (see `deployment/containers/secrets.example.yml`).
4. Node.js (for `npx`-invoked MCP servers, see `mcp/client-config.json`).

## What's codified here

```
deployment/mac/
├── install.sh              # symlinks launch-agents/*.plist into ~/Library/LaunchAgents, loads them
├── launch-agents/
│   └── com.local.lmstudio.plist   # keeps `lms server start` running across logins/restarts
├── mcp/
│   └── client-config.json         # the MCP servers block to paste into Copilot's settings
└── obsidian/
    └── plugin-settings.md         # documented Copilot / Smart Connections settings
```

MCP servers themselves are **not** daemonized here — they're stdio subprocesses that Copilot
spawns per-session via `npx`, per standard MCP client behavior, not long-running services. Only
LM Studio's server needs a persistent launch agent, since it needs to be up whenever `litellm`
on gliese routes to it.

Run `./install.sh` after `git pull` to (re)apply the LM Studio launch agent. It's idempotent —
safe to re-run.

## MCP servers

- **Apple Reminders/Calendar**: [`FradSer/mcp-server-apple-events`](https://github.com/FradSer/mcp-server-apple-events)
  — EventKit-based, ships a pre-built code-signed binary via npm (no Xcode needed), covers both
  Reminders and Calendar read/write. First run will prompt for Reminders/Calendar permission in
  System Settings — grant it once.
- **Obsidian/filesystem**: the official [`@modelcontextprotocol/server-filesystem`](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem)
  pointed at the vault directory. Considered `cyanheads/obsidian-mcp-server` instead, but it
  requires the Obsidian **Local REST API** community plugin plus an API key — the plain
  filesystem server needs no extra Obsidian-side plugin and matches the spec's "write notes
  back" requirement directly (markdown files, not an API). Replace the placeholder path in
  `mcp/client-config.json` with the real vault path.

Both are wired into Copilot via `mcp/client-config.json` — paste that block into Copilot's MCP
settings (Settings → Copilot → MCP Servers → edit as JSON).

## Privacy-critical: routing on source, not query

`litellm`'s router only sees the final prompt, not which vault notes fed it — it cannot tell
"innocuous-looking question that got RAG context injected" apart from a truly innocuous one. So
the local-only guarantee has to be enforced *here*, at the client: keep Copilot's vault-chat
mode pinned to the `local-mac` model in LiteLLM's model list, not on auto/cascading routing.
Only use OpenRouter-backed chat modes for questions that deliberately exclude vault context. See
`obsidian/plugin-settings.md`.
