# shikharbhardwaj/infra

Repo containing IaC for my homelab machines.

🚧 WIP 🚧

### Preview

![Preview image](/files/assets/images/preview.png)

### Network overview

![Network overview](/docs/diagrams/homelab-network-v3.excalidraw.png)

### Dependencies

#### bitwarden CLI with local vault

1. Download bitwarden CLI and place it in `PATH`
2. Setup connection to self-hosted

    ```
    bw config server {{ host }}
    ```
3. Login
    ```
    bw login
    ```
4. Add following rc alias to unlock vault when needed
    ```
    alias "bwu"='export BW_SESSION=$(bw unlock --raw)'
    ```

#### Ansible

1. Install pipx: https://pipx.pypa.io/stable/
2. `pipx install --include-deps ansible`
3. Populate ansible inventory in `hosts` file, using the `hosts.example` file as a
template.
4. Test ansible setup by running the following make commands (maintenance upgrades).
    ```
    make update-ubuntu-hosts
    make update-proxmox-hosts
    ```

#### Kubectl access

Download the kubectl config from `/etc/rancher/k3s/k3s.yaml` from one of the
Kubernetes nodes. Substitute things like cluster name/user name etc and place in
`~/.kube/config`

### Host inventory

| Host | Type | Role | Services |
| ---- | ---- | ---- | -------- |
| `tenzing` | Kubernetes cluster | Hosts most apps (kustomize/helm, see App inventory below) | See App inventory |
| `tyr` | Oracle Cloud VM | Public-facing utility host | traefik, crafty, uptime-kuma |
| `gliese` | Windows machine | Home services host | traefik, actual-budget, replay-hub, uptime-kuma, litellm |
| `mac` | MacBook Pro (M4 Max) | AI workspace / local model node | LM Studio, Obsidian (Copilot + Smart Connections), MCP servers |

Note: gliese overrides traefik's host-side ports (`traefik_http_port`/`traefik_https_port`/`traefik_dashboard_port` in its local `secrets.yml`) since 80/443 are already used by something else on that host.

Note: `mac` has no automated install/CD path (see [deployment/mac/](/deployment/mac/)) — it's
GUI apps and launch agents, applied by hand via `deployment/mac/install.sh`.

### App inventory

TODO: Move all these to ArgoCD.

<details>
    <summary>Kustomize</summary>

| Name | In use? | ArgoCD |
| ---- | ----- | --- |
| [autotrim-pv](/deployment/kubernetes/kustomize/autotrim-pv) | ✅ | ❌ |
| [deluge](/deployment/kubernetes/kustomize/deluge) | ✅ | ❌ |
| [homepage](/deployment/kubernetes/kustomize/homepage) | ✅ | ❌ |
| [kavita](/deployment/kubernetes/kustomize/kavita) | ✅ | ❌ |
| [letsencrypt](/deployment/kubernetes/kustomize/letsencrypt) | ✅ | ❌ |
| [main-ingress](/deployment/kubernetes/kustomize/main-ingress) | ✅ | ❌ |
| [minio](/deployment/kubernetes/kustomize/minio) | ✅ | ❌ |
| [mlflow](/deployment/kubernetes/kustomize/mlflow) | ✅ | ❌ |
| [postgres-mlflow](/deployment/kubernetes/kustomize/postgres-mlflow) | ✅ | ❌ |
| [prowlarr](/deployment/kubernetes/kustomize/prowlarr) | ✅ | ❌ |
| [radarr](/deployment/kubernetes/kustomize/radarr) | ✅ | ❌ |
| [readarr](/deployment/kubernetes/kustomize/readarr) | ✅ | ❌ |
| [shelly-plug-monitor](/deployment/kubernetes/kustomize/shelly-plug-monitor) | ✅ | ❌ |
| [sonarr](/deployment/kubernetes/kustomize/sonarr) | ✅ | ❌ |
| [ttyd](/deployment/kubernetes/kustomize/ttyd) | ✅ | ❌ |
| [vaultwarden](/deployment/kubernetes/kustomize/vaultwarden) | ✅ | ❌ |
| [wazuh](/deployment/kubernetes/kustomize/wazuh) | ✅ | ❌ |
| [docker-registry](/deployment/kubernetes/kustomize/docker-registry) | ❌ | ❌ |
| [heimdall](/deployment/kubernetes/kustomize/heimdall) | ❌ | ❌ |
| [home-assistant](/deployment/kubernetes/kustomize/home-assistant) | ❌ | ❌ |
| [csgo-dedicated-server](/deployment/kubernetes/kustomize/csgo-dedicated-server) | ❌ | ❌ |
| [tuya-monitor](/deployment/kubernetes/kustomize/tuya-monitor) | ❌ | ❌ |

</details>

<details>
    <summary>Helm charts</summary>

| Name | In use? | ArgoCD |
| ---- | ----- | --- |
| [autotrim](/deployment/kubernetes/helm-values/autotrim) | ✅ | ✅ |
| [nocodb](/deployment/kubernetes/helm-values/nocodb) | ✅ | ✅ |
| [zero2prod](/deployment/kubernetes/helm-values/zero2prod) | ✅ | ✅ |
| [argo-cd](/deployment/kubernetes/helm-values/argo-cd) | ✅ | ❌ |
| [coder](/deployment/kubernetes/helm-values/coder) | ✅ | ❌ |
| [democratic-csi](/deployment/kubernetes/helm-values/democratic-csi) | ✅ | ❌ |
| [label-studio](/deployment/kubernetes/helm-values/label-studio) | ✅ | ❌ |
| [nextcloud](/deployment/kubernetes/helm-values/nextcloud) | ✅ | ❌ |
| [triton-inference-server](/deployment/kubernetes/helm-values/triton-inference-server) | ✅ | ❌ |
| [prefect](/deployment/kubernetes/helm-values/prefect) | ❌ | ❌ |

</details>