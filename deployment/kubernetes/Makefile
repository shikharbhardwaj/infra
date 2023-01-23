deploy:
	cd $(app)/overlays/$(variant) && kubectl kustomize | envsubst | kubectl apply -f -