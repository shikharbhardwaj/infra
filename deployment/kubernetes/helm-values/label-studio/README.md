## label-studio installation

Ref: https://labelstud.io/guide/install_k8s.html

1. Helm chart repo

```
helm repo add heartex https://charts.heartex.com/
helm repo update heartex
```

2. Create namespace

```
kubectl create ns label-studio
```

3. Install a release

```
helm install label-studio --namespace label-studio heartex/label-studio -f values.yml
```