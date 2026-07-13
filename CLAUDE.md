# infra

Homelab IaC. Four hosts, four different deployment mechanisms:

- **tenzing** — Kubernetes cluster (k3s). Hosts most apps via kustomize/Helm
  under `deployment/kubernetes/`. CD via `cd.yml` (self-hosted runner ->
  `deployment/automation/deploy.sh` -> `kubectl`), unconditional on every
  push to `main`. TODO in README: migrate to ArgoCD.
- **tyr** — Oracle Cloud VM (Linux). Runs traefik, crafty, uptime-kuma, and
  `external-routes` (see below) via podman quadlets + `systemd --user`.
  Standard traefik ports (80/443/8080).
- **gliese** — Windows machine. Podman actually runs inside **WSL2**, and
  Tailscale is installed *inside that WSL2 distro directly* (not just the
  Windows host) - that's what makes Tailscale SSH land you in the right
  place. Runs traefik, actual-budget, replay-hub, litellm. Non-standard
  traefik ports (8080/8043/8081 for http/https/dashboard) since 80/443 are
  already taken by something else on that host.
- **mac** — MacBook Pro (M4 Max). No CD, no automated install - GUI apps
  (LM Studio, Obsidian) and launch agents applied by hand via
  `deployment/mac/install.sh`. See "AI stack" below.

## Container deployment (tyr/gliese)

`deployment/containers/install` is the whole mechanism: for each directory
under `deployment/containers/` listed for the current host in
`inventory.yml`, it substitutes `{{ var }}` placeholders (from a **local,
gitignored** `secrets.yml`) into every file, symlinks `*.container` quadlet
files into `~/.config/containers/systemd/`, and reloads systemd.

- `secrets.yml` lives at `~/infra/deployment/containers/secrets.yml` on each
  host (i.e. inside the git checkout, next to `install`) - that's the path
  `install` reads by default when run from that directory. It is **not**
  shared between hosts and has no fixed schema beyond "whatever `{{ vars }}`
  the containers that host installs actually reference."
- `secrets.example.yml` is the documented list of all placeholders used
  anywhere in the repo - `deployment/automation/validate-container-configs.py`
  (wired into `ci.yml`) fails the build if a `{{ var }}` is used without a
  matching key there, or if a `Secret=` directive doesn't match a
  container's `config.yml` `podman_secrets`, or if `inventory.yml`
  references a container directory that doesn't exist.
- CD is `.github/workflows/cd-containers.yml`: a self-hosted runner (on the
  Tailscale tailnet) SSHes into each host, `git pull --ff-only`, runs
  `./install --inventory inventory.yml --restart`. Auth is via **Tailscale
  SSH** (tailnet ACLs, not a keypair) - the ACL's `ssh` rule for the runner
  must use `"action": "accept"`, not the default `"check"`, or CI hangs
  waiting for an interactive browser re-auth that can never happen
  headlessly.
- **CI (`ci.yml`) and CD (`cd-containers.yml`) are independent workflows** -
  a CI failure does not block CD. This has already caused one bad deploy.

## Hard-won gotchas

- **Podman Quadlet `Label=` values containing spaces get silently
  word-split/truncated** unless the entire `key=value` is wrapped in
  quotes: `Label="traefik.http.routers.x.rule=Host(\`a\`) || Host(\`b\`)"`.
  Nothing validates this - the source file and the rendered file both look
  correct; only `podman inspect <name> --format '{{.Config.Labels}}'` on the
  actual running container reveals the truncation. Any label value with a
  space (dual-host `||` rules, anything with quotes) needs this.
- **Traefik's docker/podman label provider does not support
  `serversTransports` at all.** Confirmed via `curl
  localhost:8080/api/rawdata` - the top level only has `routers`,
  `middlewares`, `services`, no `serversTransports` key, no matter how the
  labels are written. Any serversTransport (e.g. `insecureSkipVerify` for a
  self-signed backend) has to stay in a file-provider YAML
  (`traefik/transports.yml`, static/host-agnostic, no secrets, safe to ship
  everywhere) referenced as `sometransport@file`, not `@docker`.
- **`install` only creates directories that exist in the git source tree.**
  A `Volume=%h/containers/X/somedir:...:Z` bind mount needs a real
  `X/somedir/` in git (with an `empty-file-so-git-tracks-this-dir.txt`,
  since git doesn't track empty dirs) or the container crash-loops on the
  target host with `statfs: no such file or directory`. This took down
  tyr's traefik in production once.
- **A missing `{{ var }}` in `secrets.yml` used to fail silently** - `install`
  would log a warning and write the raw `{{ var }}` text into the rendered
  config, which then failed much later with a misleading error (e.g.
  systemd `Unit not found` when quadlet couldn't parse a resulting
  `PublishPort={{ x }}:80`). `install` now has a pre-flight scan
  (`find_missing_placeholders`) that fails loudly, listing exactly which
  secrets are missing per container, before touching any file. Trust this -
  but it does *not* catch the missing-bind-mount-directory issue above,
  that's a different failure class.
- **`.lan` / `.local` domains can never get a publicly-trusted cert** - CAs
  are contractually barred from issuing for non-ICANN TLDs, and `.local` is
  separately blocklisted (reserved for mDNS). If a host needs dual local +
  public routing with a real cert on both, use a real subdomain with a
  private-network DNS record (e.g. `gliese.home.<domain>` -> LAN IP) instead
  of `gliese.lan` - DNS-01 challenges only need DNS control, not public
  reachability, so the existing Cloudflare DNS-01 setup here handles it with
  zero new infrastructure.
- **`main` has branch protection requiring PRs, but admin pushes silently
  bypass it** (`remote: Bypassed rule violations for refs/heads/main`).
  Direct pushes to `main` have been the norm in practice so far.

## external-routes

`deployment/containers/external-routes/` is a placeholder podman container
(alpine, `sleep infinity`) that exists purely to carry Traefik labels for
backends that aren't podman containers on the host at all: phoenix (Proxmox
on thor, via tailscale), media (Jellyfin, via tailscale), photos/speedtest/
drive (apps on the tenzing k8s cluster). It's listed only in tyr's
`inventory.yml` entry, which is *why* it's host-scoped correctly - Traefik's
docker provider only ever sees labels from containers on its own host's
podman socket, so gliese's traefik never discovers these routes. This
replaced a shared `dynamic.yml` (file provider) that used to be mounted on
every host running traefik, which caused gliese to try (and fail) to issue
ACME certs for routes it had no business serving.

## AI stack (Obsidian + LiteLLM + MCP)

Personal RAG/assistant stack over an Obsidian vault. Load-bearing pieces:

- **`litellm`** (`deployment/containers/litellm/`) runs on **gliese** as a normal podman
  quadlet - the single OpenAI-compatible endpoint everything else talks to. Model list lives in
  `litellm-config.yaml` (mounted into the container as `/app/config.yaml` - not to be confused
  with the container's own `config.yml` metadata for `podman_secrets`): `local-mac` (LM Studio
  on the mac, reached over Tailscale) and `openrouter-frontier` (cloud, non-sensitive only).
- **mac is model-serving only, for now.** `deployment/mac/` holds just a launch agent to keep
  LM Studio's server up, plus documented (not templated - plugin `data.json` is generated
  state) Obsidian plugin settings. No MCP servers run there.
- **`obsidian-sync-mcp`** (`deployment/containers/obsidian-sync-mcp/`) also runs on **gliese**
  as a podman quadlet - the agent that actually reads/writes the vault. It talks to
  `obsidian-couchdb` (the existing LiveSync backend on **tenzing**, see
  `deployment/kubernetes/kustomize/obsidian-couchdb`) over HTTPS via `{{ tenzing_host }}`,
  *not* the vault filesystem. The vault syncs across multiple devices via Self-hosted
  LiveSync, so a raw filesystem MCP on any one device would race LiveSync's own change
  tracking and only see that device's copy; going through CouchDB directly is the only way
  that's both device-independent and LiveSync-safe. Obsidian Copilot (wherever it's running)
  points at its `/mcp` endpoint as a remote HTTP MCP server, not a local `npx` spawn - see
  `deployment/mac/obsidian/plugin-settings.md`. Apple Reminders/Calendar MCP is deferred
  alongside this (EventKit-based, can only run on the mac, and mac is model-only for now).
- **No mirrored-networking/portproxy setup was needed.** The original design for this kind of
  stack assumes Tailscale on the Windows host + WSL2 mirrored networking so the host's LAN can
  reach a WSL2-bound port. gliese's WSL2 is already a tailnet member (see above), so anything
  on the tailnet - the mac, and eventually `luna` - reaches services bound there directly via
  its tailnet IP. Don't reintroduce that plumbing without a reason.
- **Privacy rule is enforced client-side, not in LiteLLM.** LiteLLM's router only sees the
  final prompt, not which vault notes were injected into it as RAG context, so it can't route
  on sensitivity itself. Obsidian Copilot's vault-chat mode is pinned to `local-mac`; only a
  separate, explicitly-non-vault chat mode may use `openrouter-frontier`. See
  `deployment/mac/obsidian/plugin-settings.md`.
- **`luna` (the gaming PC, RTX 5070 Ti) is deferred** - not a tracked host yet. It's the
  intended home for a real local inference server (vLLM), still undecided whether that runs as
  a bare WSL2 systemd service or a podman quadlet (GPU passthrough into podman-in-WSL2 is a
  less-proven path than a native WSL2 CUDA process). When it lands, add a model entry to
  `litellm`'s `litellm-config.yaml` and complete the fallback chain (`luna` -> mac -> cloud) - the spot
  is already marked with a `TODO(luna)` comment there.

## Known outstanding issues

- gliese's `cf_dns_api_token` is malformed or lacks Cloudflare zone access
  (`Invalid format for Authorization header`, `failed to find zone
  <domain>`). Traefik falls back to a self-signed cert there - routing
  works, but browsers show a cert warning. Needs a regenerated token from
  the Cloudflare dashboard, updated in gliese's local `secrets.yml`.

## Useful verification commands

```bash
# Dry-run install without restarting anything live
cd deployment/containers && ./install --inventory inventory.yml

# What Traefik actually resolved (not what the label file says)
curl -s http://127.0.0.1:8080/api/http/routers/<name>@docker
curl -s http://127.0.0.1:8080/api/rawdata | python3 -m json.tool

# What labels actually landed on the running container
podman inspect <name> --format '{{range $k, $v := .Config.Labels}}{{$k}}={{$v}}
{{end}}'
```
