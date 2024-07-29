```
helm repo add fluent https://fluent.github.io/helm-charts
helm upgrade --install fluent-bit fluent/fluent-bit -n observability --create-namespace -f helm-values/observability/fluent-bit/values.yml --version 0.47.5
```