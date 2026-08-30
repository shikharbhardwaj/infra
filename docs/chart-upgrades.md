# Helm chart upgrades

Third-party Helm charts are version-pinned in git. [Renovate](https://docs.renovatebot.com/)
(`renovate.json5` + `.github/workflows/renovate.yml`) watches those pins and
opens a PR when a newer version is published. Renovate only **proposes** — a
human reviews and merges, and for most targets a human also applies the result
to the cluster (see the apply matrix below).

## Why review is mandatory (chart version ≠ app version)

A chart's `version` is independent of the `appVersion` it ships. A chart
*patch* bump can carry an application *major* upgrade with breaking changes.

> Real example: immich chart `0.12.0` → `0.12.1` looked like a patch, but it
> moved Immich itself from **v2.6.3 → v3.0.0** — a major release that dropped
> pgvecto.rs support. See the immich `Application` manifest for how that
> upgrade was vetted (VectorChord already in use, x86-64-v2 CPU, removed env
> vars unused).

So Renovate is configured to **never auto-merge** chart updates, and to label
majors `chart-major-review`. Before merging any chart PR:

1. Read the chart `appVersion` delta (in the PR / the chart `Chart.yaml`).
2. Read the upstream **application** release / migration notes for that
   appVersion range — not just the chart changelog.
3. Verify this cluster meets any new preconditions (DB extensions, CPU
   baseline, removed config keys, storage).
4. If the app runs DB migrations on boot, take an on-demand CNPG backup first
   (`kubectl apply` a `Backup` targeting the cluster).

## What Renovate covers

| Target | Pinned in | Source type |
|---|---|---|
| `immich` | `deployment/kubernetes/argocd/immich.yml` | git-tagged chart (`immich-<semver>`) |
| `nextcloud` | `deployment/kubernetes/argocd/nextcloud.yml` | Helm repo |
| `tailscale-operator` | `deployment/kubernetes/helm-values/tailscale/tailscale-operator/Chart.yaml` | Helm repo dependency |

**Not covered / excluded:**

- `liftbook-staging` — your own app, pinned to a git SHA (that's app CD, not a
  dependency update).
- `tdarr` — vendored wrapper chart, `appVersion: latest` (no upstream pin).
- `helm-values/argo-cd/applications/nextcloud-prod.yaml` — stale, references an
  Application that isn't deployed; ignored in `renovate.json5`.
- `nocodb` — a live Argo app, but its `Application` is **not in git** (see
  drift note below), so Renovate can't see it yet.

## Apply matrix — what happens after a PR merges

The pins live in git, but only one target closes the GitOps loop on its own.
The rest need the `Application` object re-applied, because their `Application`
points at the *upstream* chart repo (not this infra repo), so changing
`targetRevision` in git doesn't reach the cluster until someone applies it.

| Target | After merge to `main` |
|---|---|
| `tailscale-operator` | **Automatic.** Its Application watches this infra repo at `main` with auto-sync; the merged Chart.yaml bump syncs itself. |
| `immich`, `nextcloud` | **Manual.** `kubectl apply -f <the Application yml>` then `argocd app sync <name>` (no automated syncPolicy). |
| `nocodb` (once imported) | Manual apply of the Application; its own auto-sync then rolls the chart. |

### Closing the loop (optional, removes the manual apply)

To make immich/nextcloud/nocodb as hands-off as tailscale-operator, add an
**app-of-apps**: a root Argo `Application` that watches
`deployment/kubernetes/argocd/**` in this infra repo with `automated` sync, so
merging a `targetRevision` bump auto-applies the child Application. (Alternative:
a step in `cd.yml` that `kubectl apply`s `deployment/kubernetes/argocd/*.yml` on
push to `main`.) Not yet wired up — the Applications are currently hand-applied.

## Drift: Argo Applications that live only in the cluster

`immich` (now fixed), `nocodb`, `liftbook-staging`, and `tailscale-operator`
were all applied to the cluster by hand and are **not** all mirrored in git.
The `argocd/` manifests that *are* in git are not wired into CD
(`deployment/automation/list-live-targets.py` only picks up kustomize dirs with
a live `config.json`) — they're applied by hand, same as the upstream nextcloud
precedent. Import the remaining live Applications into `argocd/` (as immich was)
to bring them under Renovate + review, and to enable the app-of-apps above.

## Setup / operation

- **Secret:** the workflow needs `RENOVATE_TOKEN` — a fine-grained PAT scoped to
  this repo with **Contents: read/write** and **Pull requests: read/write**.
  (The default `GITHUB_TOKEN` is avoided so Renovate's PRs can trigger `ci.yml`.)
- **Cadence:** scheduled weekly (Mon 05:30 IST); PRs are also gated to a
  Monday-morning window in `renovate.json5`.
- **Manual run / first test:** `Actions → renovate → Run workflow`, with
  **Dry run** checked to see what it *would* do without opening PRs.
- **Backlog:** Renovate maintains a "Dependency Dashboard" issue listing every
  pending update.
