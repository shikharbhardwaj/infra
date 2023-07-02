VERSION:=25.0.8-apache

build-docker:
	docker build -t mlflow:latest .

push-docker: build-docker
	docker tag mlflow:latest ghcr.io/shikharbhardwaj/nextcloud:$(VERSION)
	docker push ghcr.io/shikharbhardwaj/nextcloud:$(VERSION)