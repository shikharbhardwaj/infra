
```
helm repo add immich https://immich-app.github.io/immich-charts
helm install --create-namespace --namespace immich immich immich/immich -f values.yaml
```