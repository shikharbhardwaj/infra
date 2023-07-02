SHELL := /bin/bash

current_dir = $(shell pwd)

deploy:
	cd manifests/$(app)/overlays/$(variant) && kubectl kustomize | $(current_dir)/tools/substitute | kubectl apply -f -

substitute:
	cat $(file) | $(current_dir)/tools/substitute > out/dst.yml