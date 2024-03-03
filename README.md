# shikharbhardwaj/infra

Repo containing IaC for my homelab machines.

🚧 WIP 🚧

### Preview

![Preview image](/files/assets/images/preview.png)

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

### App inventory

TODO: Move all these to ArgoCD.

<details>
    <summary>Kustomize</summary>

| Name | In use? | ArgoCD |
| ---- | ----- | --- |
| [autotrim-pv](/deployment/kubernetes/manifests/autotrim-pv) | ✅ | ❌ |
| [deluge](/deployment/kubernetes/manifests/deluge) | ✅ | ❌ |
| [homepage](/deployment/kubernetes/manifests/homepage) | ✅ | ❌ |
| [kavita](/deployment/kubernetes/manifests/kavita) | ✅ | ❌ |
| [letsencrypt](/deployment/kubernetes/manifests/letsencrypt) | ✅ | ❌ |
| [main-ingress](/deployment/kubernetes/manifests/main-ingress) | ✅ | ❌ |
| [minio](/deployment/kubernetes/manifests/minio) | ✅ | ❌ |
| [mlflow](/deployment/kubernetes/manifests/mlflow) | ✅ | ❌ |
| [postgres-mlflow](/deployment/kubernetes/manifests/postgres-mlflow) | ✅ | ❌ |
| [prowlarr](/deployment/kubernetes/manifests/prowlarr) | ✅ | ❌ |
| [radarr](/deployment/kubernetes/manifests/radarr) | ✅ | ❌ |
| [readarr](/deployment/kubernetes/manifests/readarr) | ✅ | ❌ |
| [shelly-plug-monitor](/deployment/kubernetes/manifests/shelly-plug-monitor) | ✅ | ❌ |
| [sonarr](/deployment/kubernetes/manifests/sonarr) | ✅ | ❌ |
| [ttyd](/deployment/kubernetes/manifests/ttyd) | ✅ | ❌ |
| [vaultwarden](/deployment/kubernetes/manifests/vaultwarden) | ✅ | ❌ |
| [wazuh](/deployment/kubernetes/manifests/wazuh) | ✅ | ❌ |
| [docker-registry](/deployment/kubernetes/manifests/docker-registry) | ❌ | ❌ |
| [heimdall](/deployment/kubernetes/manifests/heimdall) | ❌ | ❌ |
| [home-assistant](/deployment/kubernetes/manifests/home-assistant) | ❌ | ❌ |
| [csgo-dedicated-server](/deployment/kubernetes/manifests/csgo-dedicated-server) | ❌ | ❌ |
| [tuya-monitor](/deployment/kubernetes/manifests/tuya-monitor) | ❌ | ❌ |

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