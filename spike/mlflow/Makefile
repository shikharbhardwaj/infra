build-docker:
	docker build -t mlflow:latest .

push-docker:
	docker tag ghcr.io/shikharbhardwaj/mlflow:$(VERSION) mlflow:latest
	docker push ghcr.io/shikharbhardwaj/mlflow:$(VERSION)