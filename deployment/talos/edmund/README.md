# edmund

Single-node Talos Kubernetes cluster, running as a VM on **saras**, with all
persistent state on **truenas-saras** (the TrueNAS SCALE VM on the same host)
via [truenas-csi](https://github.com/truenas/truenas-csi) - TrueNAS's official
CSI driver, which uses the WebSocket JSON-RPC API (democratic-csi, used on
tenzing, still talks to the REST API that TrueNAS 26 removes).

Intended home for the apps moving off gliese (actual-budget, ah-invoices,
litellm + its Postgres, replay-hub) so gliese can become wake-on-LAN only.

| Piece | Version |
| --- | --- |
| Talos | v1.14.2 (Kubernetes v1.37.1) |
| truenas-csi chart | 1.3.0 |
| external-snapshotter | v8.6.0 |
| TrueNAS (truenas-saras) | SCALE 25.10.6 |

## Layout

- `schematic.yaml` - Image Factory schematic (iscsi-tools, util-linux-tools,
  qemu-guest-agent, tailscale). Its ID is pinned in `patches/install.yaml` and
  the ISO URL below.
- `patches/` - Talos machine config patches committed to git.
- `gen-config.sh` - renders `out/controlplane.yaml` + `out/talosconfig` from
  the patches plus host-specific values (LAN IP/subnet, tailscale auth key).
- `secrets.vault.yaml` - the cluster secrets bundle, ansible-vault encrypted
  (vault password via `pass.sh`). `gen-config.sh` restores `out/` from it.
- `csi/` - truenas-csi namespace and Helm values (StorageClasses
  `truenas-iscsi` (default) and `truenas-nfs`, both `Retain`).
- `out/` - gitignored. **`out/secrets.yaml` is the cluster's root of trust** -
  its durable copy is `secrets.vault.yaml` (above).

## Networking

- **In-cluster endpoint is the LAN IP** (`https://<NODE_LAN_IP>:6443`). The
  node has no MagicDNS, so it can't resolve `edmund` itself.
- **Clients (laptop, CD runner) use the tailnet name `edmund`**. The node
  joins the tailnet via the tailscale extension. kubelet and etcd are pinned
  to `LAN_SUBNET` so they never pick the tailscale interface.
- `NODE_LAN_IP` must be stable: set a DHCP reservation for the VM's MAC.

## Ingress

`platform/` holds cert-manager and Traefik, both installed by the playbook.

- **Traefik** binds the node's 80/443 via hostPort; there's no LoadBalancer
  on a single node. HTTP redirects to HTTPS. Ingresses use the default
  `traefik` IngressClass.
- **Hostnames are `<app>.edmund.<parent_host>`.** Public Cloudflare DNS has
  `edmund` and `*.edmund` A records pointing at the node's **tailnet IP**
  (DNS only, not proxied). That's the same pattern as `*.tenzing.` and
  `*.gliese.`: reachable from the tailnet, including tyr's traefik for
  anything that needs public exposure.
- **TLS:** the `letsencrypt` ClusterIssuer (Cloudflare DNS-01, the same token
  as tenzing) issues one wildcard cert, `edmund-wildcard-tls` in the
  `traefik` namespace. Traefik's default TLSStore serves it, so an Ingress
  needs no `tls:` block or Certificate of its own for an `*.edmund.` host.
  Other hosts (e.g. a `*.<parent_host>` name) need their own Certificate
  from the same ClusterIssuer.

## Postgres

CloudNativePG operator 1.30.1 plus the **Barman Cloud Plugin** v0.15.1, both
in `cnpg-system` and installed by the playbook. Clusters use the operator's
default image (minimal flavour) and back up through the plugin: an
`ObjectStore` CR plus `spec.plugins: [{name: barman-cloud.cloudnative-pg.io,
...}]` on the Cluster. **Not** in-tree `backup.barmanObjectStore` as on
tenzing. That's deprecated, removed in CNPG 1.31, and only works with the
deprecated `system` images.

## Apps and CD

Apps live in `apps/<app>/`: a kustomization with double-brace placeholders
rendered from the k8s ansible vault. **They deploy via CD, not by hand:**
`.github/workflows/cd-edmund.yml` runs `deployment/automation/deploy-edmund.sh`
on the self-hosted (tailnet) runner on every push to `main` that touches
`apps/`, the vault or the deploy tooling. It can also be triggered manually
(workflow_dispatch). It applies each app with
`make -C deployment/kubernetes edmund-deploy app=<app>`, which pins
`--context edmund`.

CD authenticates as the `cd-deployer` ServiceAccount
(`platform/cd/deployer.yaml`, created by the playbook). The
`EDMUND_KUBECONFIG` GitHub secret holds a kubeconfig for its token, with the
server set to `https://edmund:6443`. To rotate or revoke it, delete the
`cd-deployer-token` Secret. To re-issue it, re-apply `deployer.yaml`,
rebuild the kubeconfig from the new token, and `gh secret set
EDMUND_KUBECONFIG`.

## Bootstrap

**Automated:** `make bootstrap-edmund` (`playbooks/bootstrap-edmund.yml`)
does steps 2-4 below end to end, and is safe to re-run. Do step 1 first. You
also need:
- talosctl 1.14.2, kubectl and helm on the machine running it;
- that machine on saras's LAN (the first apply goes to the LAN IP, before
  tailscale is up);
- a DHCP reservation for the VM's fixed MAC `BC:24:11:ED:00:01` ->
  `edmund_lan_ip`;
- `edmund_tailscale_authkey` in the vault alongside the step-1 keys.

The playbook creates VM 210 on saras and sets the TrueNAS VM (200) to
`startup: order=1,up=120`. It never changes an existing VM's hardware, and
never re-applies config to an already-configured node. Do those by hand.
The manual steps below are the fallback, and also document what it does.

### 1. TrueNAS (truenas-saras)

1. Create the parent datasets `main/k8s/edmund/iscsi` and
   `main/k8s/edmund/nfs`.
2. Enable and start the **iSCSI** and **NFS** services, and add an iSCSI
   portal (Shares → iSCSI → Portals) listening on truenas-saras's own IP
   (`truenas_saras_ip`), port 3260. Without it, iSCSI PVCs fail with
   `no iSCSI portal found matching address`. The driver matches the portal
   by exact address, so `0.0.0.0` won't do, and it never creates one itself.
3. Create an API key for the driver (ideally under a dedicated admin user).
4. Add these keys to the ansible vault
   (`deployment/kubernetes/tools/group_vars/all/vault.yml`):
   `truenas_saras_ip`, `truenas_saras_csi_api_key`, `edmund_lan_ip`.

### 2. Proxmox VM on saras

- VM ID 210, NIC on `vmbr0` with MAC `BC:24:11:ED:00:01`.
- ISO: `https://factory.talos.dev/image/8cdf4cd0a3a9fa4771aab65437032804940f2115b1b1ef6872274dde261fa319/v1.14.2/metal-amd64.iso`
- 4 vCPU, **CPU type `host`** (Talos needs x86-64-v2; the default `kvm64`
  lacks it), 8 GiB RAM with **ballooning off**, 40 GiB disk on VirtIO SCSI
  (it must show up as `/dev/sda`).
- Options: **QEMU Guest Agent enabled**, start at boot.
- **Start/shutdown order: after the TrueNAS VM, with a startup delay.**
  Otherwise PVCs fail to attach on a cold boot of saras.

### 3. Render and apply the machine config

```bash
# Tailscale auth key: reusable=false, pre-approved; tag per your ACLs.
NODE_LAN_IP=... LAN_SUBNET=10.42.0.0/16 TS_AUTHKEY=tskey-... ./gen-config.sh
# -> encrypt + commit it now: ansible-vault encrypt --vault-password-file ../../../pass.sh --output secrets.vault.yaml out/secrets.yaml

# From a machine on saras's LAN, while the VM is in maintenance mode:
talosctl apply-config --insecure -n "$NODE_LAN_IP" --file out/controlplane.yaml
```

The node installs to disk, reboots and joins the tailnet as `edmund`. From
then on, use the talosconfig, which already targets `edmund`:

```bash
export TALOSCONFIG=$PWD/out/talosconfig
talosctl bootstrap
talosctl health
talosctl kubeconfig out/kubeconfig
# The generated kubeconfig points at the LAN IP - switch it to the tailnet name.
kubectl --kubeconfig out/kubeconfig config set-cluster edmund --server=https://edmund:6443
```

### 4. Snapshot controller + truenas-csi

```bash
export KUBECONFIG=$PWD/out/kubeconfig
kubectl apply -k 'https://github.com/kubernetes-csi/external-snapshotter/client/config/crd?ref=v8.6.0'
kubectl apply -k 'https://github.com/kubernetes-csi/external-snapshotter/deploy/kubernetes/snapshot-controller?ref=v8.6.0'

kubectl apply -f csi/namespace.yaml
# Render vault secrets into the values (needs BW_SESSION, see deployment/kubernetes/README.md).
../../kubernetes/tools/substitute < csi/values.yaml > out/csi-values.yaml
helm repo add truenas-csi https://raw.githubusercontent.com/truenas/truenas-csi/master/charts
helm upgrade --install truenas-csi truenas-csi/truenas-csi --version 1.3.0 \
  -n truenas-csi -f out/csi-values.yaml
```

### 5. Smoke test

Create one PVC per StorageClass and mount each in a pod. Check that the
zvol/dataset appears under `main/k8s/edmund/` in TrueNAS and that a write
survives a pod restart. Do this before migrating any app.

## Follow-ups

- **Talos workload isolation is off** (`patches/single-node.yaml`). The 1.14
  sandbox is expected to break truenas-csi's `nsenter` into `/proc/1` for
  `iscsiadm`. This is inferred, not verified. Test it once the smoke test
  passes: enable it, reboot, and re-attach an iSCSI PVC. If that works, keep
  it on.
- **Not set up yet:** node_exporter/vmagent scrape job, app migration from gliese.
