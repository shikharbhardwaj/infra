---
name: kubernetes-app-manager
description: Safely add and modify applications, Kustomize manifests, Helm values, ingress, storage, and deployment automation for the tenzing k3s cluster.
---

# Kubernetes App Manager

Use this skill for `deployment/kubernetes/` workloads and their deployment automation.

## Rules

- Read `deployment/kubernetes/README.md` and the target app's README/config before editing.
- Treat `deployment/hosts.yml` as the canonical physical/VM inventory; do not confuse it with Kubernetes app inventory.
- Preserve the repository's Kustomize/Helm structure, naming, namespaces, labels, storage classes, and ingress conventions.
- Keep secrets out of manifests and Git. Use the existing substitution/bootstrap mechanism and document required local inputs.
- Review resource requests/limits, persistent storage, service ports, probes, and ingress/TLS impacts together.
- Do not assume ArgoCD is already authoritative; current CD uses `.github/workflows/cd.yml` and `deployment/automation/deploy.sh`.

## Workflow

1. Locate the app, base/overlay, Helm values, generated config, and live-target metadata.
2. Check analogous applications before introducing a new pattern.
3. Make a minimal manifest/configuration change.
4. Run repository checks:

```bash
./deployment/automation/check-kustomize-configs.sh
./deployment/automation/test-gen-configs.sh
make -C deployment/kubernetes
```

Use `kubectl diff`/`kubectl apply --dry-run=server` only when a configured cluster is intentionally available; never require cluster credentials for static validation.

5. Review rendered YAML, `git diff --check`, rollout behavior, and potential downtime. Clearly state namespace, workload, PVC, ingress, and deployment effects.
