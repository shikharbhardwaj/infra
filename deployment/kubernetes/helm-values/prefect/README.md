## Prefect helm chart

Source: https://github.com/PrefectHQ/prefect-helm

### Steps

```
helm repo add prefect https://prefecthq.github.io/prefect-helm/
helm repo update
helm search repo prefect
helm install --create-namespace --namespace prefect --values ./../../out/dst.yml prefect-server prefect/prefect-server
```
