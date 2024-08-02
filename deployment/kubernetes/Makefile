SHELL := /bin/bash

current_dir = $(shell pwd)

deploy:
	cd kustomize/$(app)/overlays/$(variant) && kubectl kustomize | $(current_dir)/tools/substitute | kubectl apply -f -

substitute:
	cat $(file) | $(current_dir)/tools/substitute > out/dst.yml

edit-secrets:
	cd tools && ansible-vault edit group_vars/all/vault.yml
