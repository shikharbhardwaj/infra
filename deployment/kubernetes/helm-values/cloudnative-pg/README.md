## CloudNativePG

Ref: https://github.com/cloudnative-pg/charts

### Steps

```
helm repo add cloudnative-pg https://cloudnative-pg.io/charts/
```

```
helm upgrade --install --values helm-values/cloudnative-pg/values.yml cloudnative-pg --namespace cloudnative-pg cloudnative-pg/cloudnative-pg --version 0.20.2
```