# mac

The MacBook Pro (M4 Max) is a tracked host in this repo, but unlike `tenzing`/`tyr`/`gliese`
there's no automated CD path here — no self-hosted runner reaches a laptop that sleeps and
roams, and the load-bearing piece (LM Studio) is a GUI app with no headless install mechanism.

**For the moment, mac's role in the AI stack is model serving only** — LM Studio, reached over
Tailscale by `litellm` on gliese. Anything that acts on the Obsidian vault (MCP tooling) runs on
gliese instead, against the vault's CouchDB LiveSync backend, so it works regardless of which
device is awake — see `deployment/containers/obsidian-sync-mcp/` and the "AI stack" section in
the root `CLAUDE.md`. Apple Reminders/Calendar MCP (EventKit-based, so it can only ever run on
a Mac) is deferred along with that.

## Prerequisites (manual, one-time)

1. [LM Studio](https://lmstudio.ai/) installed, with the CLI bootstrapped
   (`Cmd+Shift+P` → "Bootstrap CLI" in-app, or `~/.lmstudio/bin/lms bootstrap`) so `lms` is on
   `PATH`. Load whatever model you want resident (see `deployment/containers/litellm/litellm-config.yaml`
   on gliese for the model name the proxy expects — keep them in sync).
2. [Obsidian](https://obsidian.md/) with the vault opened (synced via Self-hosted LiveSync),
   plus the community plugins **Copilot** and **Smart Connections** installed and enabled
   (Settings → Community plugins → Browse). Plugin *install* is manual; plugin *settings* are
   documented in `obsidian/plugin-settings.md`.
3. [Tailscale](https://tailscale.com/download/mac) installed and joined to the same tailnet as
   `tyr`/`gliese`/`tenzing`. This is what lets the `litellm` proxy on `gliese` reach LM Studio
   here (`http://<mac-tailscale-ip>:1234/v1`). Get the IP with `tailscale ip -4` and put it in
   gliese's `secrets.yml` as `mac_tailscale_ip` (see `deployment/containers/secrets.example.yml`).

## What's codified here

```
deployment/mac/
├── install.sh              # symlinks launch-agents/*.plist into ~/Library/LaunchAgents, loads them
├── launch-agents/
│   └── com.local.lmstudio.plist   # keeps `lms server start` running across logins/restarts
└── obsidian/
    └── plugin-settings.md         # documented Copilot / Smart Connections settings
```

Run `./install.sh` after `git pull` to (re)apply the LM Studio launch agent. It's idempotent —
safe to re-run.

## Privacy-critical: routing on source, not query

`litellm`'s router only sees the final prompt, not which vault notes fed it — it cannot tell
"innocuous-looking question that got RAG context injected" apart from a truly innocuous one. So
the local-only guarantee has to be enforced *here*, at the client: keep Copilot's vault-chat
mode pinned to the `local-mac` model in LiteLLM's model list, not on auto/cascading routing.
Only use OpenRouter-backed chat modes for questions that deliberately exclude vault context. See
`obsidian/plugin-settings.md`.
