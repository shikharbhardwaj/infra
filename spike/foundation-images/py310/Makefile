GIT_SHA := $(shell git rev-parse --short=8 HEAD)

build-docker:
	docker build -t py310:latest .

push-docker: build-docker
	docker tag py310:latest ghcr.io/shikharbhardwaj/py310:$(GIT_SHA)
	docker push ghcr.io/shikharbhardwaj/py310:$(GIT_SHA)

