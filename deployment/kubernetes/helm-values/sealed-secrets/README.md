## Bitnami Sealed secrets

https://github.com/bitnami-labs/sealed-secrets?tab=readme-ov-file#helm-chart

```
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm install sealed-secrets -n kube-system --set-string fullnameOverride=sealed-secrets-controller sealed-secrets/sealed-secrets
```