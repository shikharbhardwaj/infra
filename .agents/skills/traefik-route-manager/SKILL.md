---
name: traefik-route-manager
description: Add and review Traefik routes across Podman hosts and external backends without host-scope, label-parsing, TLS, or provider mistakes.
---

# Traefik Route Manager

Use this skill when adding HTTP/TCP routes, middleware, certificates, external services, or Traefik labels.

## Architecture

- `tyr` uses ports 80/443/8080; `gliese` uses 8080/8043/8081.
- Podman labels are discovered only by the Traefik instance on the same host.
- `external-routes` exists on `tyr` specifically for non-Podman backends such as Tailscale and tenzing services.
- Shared static/dynamic details belong in the appropriate Traefik file-provider YAML, not in host-inappropriate container inventories.

## Rules

- Keep routes host-scoped in `deployment/containers/inventory.yml`.
- Quote the complete Quadlet label assignment when a rule contains spaces, `||`, or embedded quotes:

```ini
Label="traefik.http.routers.example.rule=Host(`one.example`) || Host(`two.example`)"
```

- Traefik's Podman/docker label provider does not support `serversTransports`. Define transports in `traefik/transports.yml` and reference `name@file`.
- Use real public subdomains for publicly trusted certificates; `.lan` and `.local` cannot receive public CA certificates.
- For remote backends, use the documented Tailscale address and check network reachability from the Traefik container.

## Workflow

1. Determine the owning Traefik host and backend location.
2. Inspect neighboring routes for naming, entrypoints, TLS resolver, middleware, and network conventions.
3. Implement the smallest route change.
4. Validate container metadata and, when available, inspect the live result:

```bash
python3 deployment/automation/validate-container-configs.py
curl -s http://127.0.0.1:8080/api/rawdata | python3 -m json.tool
podman inspect <container> --format '{{range $k, $v := .Config.Labels}}{{$k}}={{$v}}\n{{end}}'
```

5. Check router status, backend reachability, certificate issuance scope, and whether a restart is actually needed.
