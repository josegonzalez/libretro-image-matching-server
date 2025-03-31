PORT ?= 5000

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

curl-text-sfc:
	curl -i -X POST -H "Content-Type: text/plain" http://127.0.0.1:8000/matches/SFC --data-binary "@SFC.txt"

curl-json-sfc:
	curl -i -X POST http://127.0.0.1:8000/matches/SFC --data-binary "@SFC.txt"
