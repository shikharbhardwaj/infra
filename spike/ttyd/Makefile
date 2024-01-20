GIT_SHA := $(shell git rev-parse --short=8 HEAD)

build-docker:
	docker build -t ttyd:latest .

push-docker: build-docker
	docker tag ttyd:latest ghcr.io/shikharbhardwaj/ttyd:$(GIT_SHA)
	docker push ghcr.io/shikharbhardwaj/ttyd:$(GIT_SHA)

run-docker:
	docker run -it --rm -p 7681:7681 ttyd:latest

