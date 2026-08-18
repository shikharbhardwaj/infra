---
name: secret-safe-infrastructure-editor
description: Edit infrastructure configuration without leaking credentials, breaking placeholder validation, or committing host-local secrets.
---

# Secret-Safe Infrastructure Editor

Use this skill for credentials, templated configuration, authentication, DNS tokens, API keys, passwords, private endpoints, and secret references.

## Rules

- Treat `**/secrets.yml`, `hosts`, `host_vars/`, and local kubeconfig/password files as sensitive. Do not open or modify them unless the user explicitly asks for a local operational action; never commit them.
- Do not echo secret values in command output, patches, logs, or final responses.
- Keep committed examples and schemas value-free. Add placeholder names to `deployment/containers/secrets.example.yml` when a new template variable is introduced.
- A `{{ name }}` placeholder must be declared in the relevant example file, unless it is inside a configured `render_exclude` file containing another tool's templating syntax.
- Podman secret names must be consistent across `.container`, `config.yml`, and the example secret catalogue.
- Prefer environment injection, Podman secrets, Ansible Vault/Bitwarden workflows, or existing local secret files over inline values.
- Never weaken TLS verification or authentication merely to make a deployment pass. If a self-signed backend is required, use the documented Traefik file-provider transport.

## Workflow

1. Identify whether a value is a secret, configuration, or public identifier.
2. Search for the placeholder/reference without printing values:

```bash
rg -n --glob '!**/secrets.yml' '{{|Secret=|password|token|api[_-]?key' .
```

3. Update only metadata/examples and references needed for the change.
4. Run the applicable validators, then inspect the diff for accidental values:

```bash
python3 deployment/automation/validate-container-configs.py
git diff --check
git status --short
```

5. Report required local secret changes by key name and host, never by value.
