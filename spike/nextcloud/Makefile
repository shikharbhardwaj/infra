VERSION:=26.0.3-apache

build-docker:
	docker build -t mlflow:latest .

push-docker: build-docker
	docker tag mlflow:latest ghcr.io/shikharbhardwaj/nextcloud:$(VERSION)
	docker push ghcr.io/shikharbhardwaj/nextcloud:$(VERSION)