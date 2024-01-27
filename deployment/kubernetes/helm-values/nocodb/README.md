## NocoDB

Installed from official helm chart at: https://github.com/nocodb/nocodb/tree/develop/charts/nocodb
Maintained in ArgoCD.

Modifications to default values:

```
parameters:
  - name: storage.storageClassName
    value: <placeholder>
  - name: global.storageClass
    value: <placeholder>
  - name: postgresql.auth.postgresPassword
    value: <placeholder>
  - name: postgresql.auth.password
    value: <placeholder>
  - name: global.postgresql.auth.database
    value: <placeholder>
  - name: postgresql.primary.podSecurityContext.enabled
    value: <placeholder>
  - name: postgresql.enabled
    value: <placeholder>
  - name: extraSecretEnvs.NC_PUBLIC_URL
    value: <placeholder>
  - name: extraSecretEnvs.NC_AUTH_JWT_SECRET
    value: <placeholder>
  - name: extraSecretEnvs.NC_DB
    value: <placeholder>
```