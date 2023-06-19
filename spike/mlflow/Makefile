build-docker:
	docker build -t mlflow:latest .

push-docker: build-docker
	docker tag mlflow:latest ghcr.io/shikharbhardwaj/mlflow:$(VERSION)
	docker push ghcr.io/shikharbhardwaj/mlflow:$(VERSION)