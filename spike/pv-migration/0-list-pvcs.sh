#!/bin/bash
kubectl get pvc -A --output=json | jq -r '.items[] | select(.spec.storageClassName == "freenas-nfs-csi") | [.metadata.namespace, .metadata.name, .spec.volumeName] | @tsv' > pvc-list.txt