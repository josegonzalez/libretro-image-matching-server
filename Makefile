PORT ?= 8000
EMU ?= FC

install:
	pip install -r requirements.txt

run:
	poetry run uvicorn main:app --host 0.0.0.0 --port $(PORT)

dev:
	poetry run fastapi dev main.py

build:
	BUILDKIT_HOST="docker-container://buildkit" railpack build --name savant/libretro-image-matching-server:latest --progress plain .

docker-run:
	docker run -it --rm savant/libretro-image-matching-server:latest

buildkit:
	docker run --rm --privileged -d --name buildkit moby/buildkit || true

curl-text:
	curl -i -X POST -H "Content-Type: text/plain" http://127.0.0.1:$(PORT)/matches/$(EMU)/snap --data-binary "@fixtures/$(EMU).txt"

curl-json:
	curl -i -X POST http://127.0.0.1:$(PORT)/matches/$(EMU)/snap --data-binary "@fixtures/$(EMU).txt"
