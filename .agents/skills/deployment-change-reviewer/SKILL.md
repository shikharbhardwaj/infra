---
name: deployment-change-reviewer
description: Review infrastructure changes for blast radius, downtime, deployment path, secret impact, and verification steps before applying them.
---

# Deployment Change Reviewer

Use this skill before committing or deploying changes in this homelab IaC repository.

## Review checklist

Classify the change by mechanism and target:

- Ansible OS maintenance: `playbooks/`, `hosts`, `Makefile`
- Kubernetes/k3s: `deployment/kubernetes/`, `cd.yml`
- Podman Quadlets: `deployment/containers/`, `cd-containers.yml`
- macOS manual setup: `deployment/mac/`
- Monitoring: vmagent, VictoriaMetrics, vmalert, Grafana

For every change, identify:

- affected host(s), services, namespaces, and files;
- whether CI and/or CD runs, noting that container CI and CD are independent;
- restart, rollout, certificate, DNS, storage, and network effects;
- secret or local-only prerequisites;
- rollback strategy;
- exact dry-run and post-deploy verification commands.

## Required checks

Run the narrowest relevant checks, then inspect the complete diff:

```bash
git diff --check
git status --short
python3 deployment/automation/validate-container-configs.py
./deployment/automation/check-kustomize-configs.sh
```

Only run commands applicable to the changed subsystem. Do not run mutating Ansible, `kubectl apply`, container installation with restart flags, or Git commits without explicit user authorization.

## Final review format

Summarize:

1. **Scope** — hosts/services affected.
2. **Risk** — likely failure modes and downtime.
3. **Validation** — commands run and results.
4. **Deployment** — what will happen automatically versus manually.
5. **Rollback** — safest reversal and any data considerations.

Never include secret values in the review.
