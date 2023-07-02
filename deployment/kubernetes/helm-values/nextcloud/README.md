## Nextcloud installation

Helm chart source: https://github.com/nextcloud/helm

### Installation/Upgrade

#### Add helm repo

```
helm repo add nextcloud https://nextcloud.github.io/helm/
```

#### Install helm chart

```
make substitute file=helm-values/nextcloud/values.yml
helm upgrade --install --values out/dst.yml --namespace nextcloud --create-namespace nextcloud nextcloud/nextcloud
```

#### Install Letsencrypt cert and ingress

```
make deploy app=letsencrypt variant=nextcloud
make deploy app=main-ingress variant=dev
```