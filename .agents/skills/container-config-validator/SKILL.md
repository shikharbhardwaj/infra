---
name: container-config-validator
description: Safely validate and modify Podman Quadlet container definitions, inventories, templated configuration, secrets metadata, and change-scoped restarts in deployment/containers.
---

# Container Config Validator

Use this skill when changing `deployment/containers/` or its install/validation tooling.

## Repository rules

- Read `AGENTS.md` and the relevant container `README.md`/`config.yml` first.
- `inventory.yml` determines which containers belong on each host; do not add a container globally when it is host-specific.
- `secrets.yml` is local and gitignored. Never create, read, or commit real secret values. Document new placeholders in `secrets.example.yml`.
- `config.yml`'s `podman_secrets` must exactly match `Secret=` directives in the corresponding `.container` file.
- Files listed by `render_exclude` contain foreign `{{ }}` syntax and must not be templated.
- Every bind-mounted source directory must exist in the source tree, usually with `empty-file-so-git-tracks-this-dir.txt`.
- Quadlet `Label=` values containing spaces must quote the complete `key=value` assignment.

## Workflow

1. Inspect the container, inventory entry, mounts, labels, networks, and dependencies.
2. Make the smallest change, preserving host scoping and rootless/systemd conventions.
3. Run validation from the repository root:

```bash
python3 deployment/automation/validate-container-configs.py
cd deployment/containers && ./install --inventory inventory.yml
```

The install command is a dry run unless restart flags are supplied. Use `--restart` only when explicitly requested; use `--restart-all` only for recovery or intentional image refreshes.

4. Review `git diff --check` and confirm no rendered files or secrets are staged.
5. If deployment is requested, explain affected host/container units and verify with systemd/podman and Traefik API inspection.

## Do not

- Put `serversTransport` in Podman labels; define it in Traefik's file provider and reference it with `@file`.
- Use `localhost` for a host service from inside a container; use the documented Tailscale address.
- Assume CI blocks CD: `.github/workflows/ci.yml` and `cd-containers.yml` are independent.
