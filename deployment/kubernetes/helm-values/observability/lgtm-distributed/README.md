# LGTM-distributed

Chart source: https://artifacthub.io/packages/helm/grafana/lgtm-distributed

```
helm repo add grafana https://grafana.github.io/helm-charts
helm upgrade --install lgtm-distributed grafana/lgtm-distributed -n observability --create-namespace -f values.yml --version 2.1.0
```