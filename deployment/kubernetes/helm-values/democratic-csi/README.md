## Persistent volumes using the democratic-csi driver

PVCs in the cluster are configured using [democratic-csi](https://github.com/democratic-csi/democratic-csi)
driver, using NFS volumes sourced from a TrueNAS instance.

### Commands

1. Substitute secrets in values.yml

```
cat ./helm-values/democratic-csi/democratic-csi-conf.yaml | tools/substitute > out/dst.yml
```

2. Helm install NFS release

```
helm upgrade --install --values out/dst.yml --namespace democratic-csi --create-namespace freenas-api-nfs democratic-csi/democratic-csi
```

3. Helm install iSCSI release

```
helm upgrade --install --values out/dst.yml --namespace democratic-csi --create-namespace freenas-api-iscsi democratic-csi/democratic-csi
```