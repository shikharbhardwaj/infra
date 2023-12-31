## Kubernetes deployment manifests

This directory is the home for the Kubernetes manifests for various apps hosted
in the homelab cluster. Given below are some frequently used commands (FUCs)
which are useful for creating/updating apps deployed using these.

### Overview

Each app is organized into its own subfolder, with Kustomize variants for
different installations (namespaces). Most apps only have a singular variant for
the installation in the `dev` namespace.

Any secret information is maintained in an Ansible-managed vault, which is
substiuted into the manifests and applied to the cluster when the `deploy` make
command is executed. To decrypt the secrets, we need to unlock a bitwarden vault.

The make commands are not context-aware ie. the user has to make sure that the
current context is set to the right cluster.

### Ingress setup

Most of the services hosted in the cluster are exposed via the ingress called
`main-ingress`. The ingress is configured using the Traefik Ingress Controller
built into K3s. It also handles TLS termination using certificates supplied by
`cert-manager`. `cert-manager` in turn works using Let's Encrypt and its
CloudFlare integration to solve the DNS-01 ACME challenge using the auth
credentials supplied as a secret.

Since the ingress cannot route to services in other namespaces, we create
separate variants for those namespaces.

### Helm installations

Several apps are also installed via Helm, in case the packaging was suitable.
Most apps installed via Helm using a customized value of `values.yaml` have a
record in the `helm-values` directory, along with a README for a hint at the
changes.

### FUCs

* Authenticate

The secrets referenced in the manifests are decrypted using credentials stored
in a Bitwarden vault, which needs to be unlocked to execute any deployment
commands.

```
export BW_SESSION=$(bw unlock --raw)
```

* Creating a new app

The `bootstrap` script in the `tools` directory creates a new instance of an
app, substituting a couple of variables from the templates kept in the
`templates` directory. It also creates a `dev` variant by default.

```
./tools/bootstrap --template-vars image=<IMAGE TAG> <APP NAME>
```

* Deploying an app

```
make deploy app=<APP NAME> variant=<VARIANT>
```

* Adding/updating secrets

```
make edit-secrets
```

### TODOs

* Software lifecycle
    * (Semi)-automated docker image updates to fix vulnerabilities, get latest
      fixes/updates from upstream.
    * Inventory of current software stack to retire unused apps, review usage over time.
    * CD configured via Github actions/Argo (?).
* Disaster recovery
    * Start documenting steps for disaster recovery.