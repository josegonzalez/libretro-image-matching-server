install:
	pip install -r requirements.txt

run:
	uvicorn main:app --reload

dev:
	fastapi dev main.py

curl-text-sfc:
	curl -i -X POST -H "Content-Type: text/plain" http://127.0.0.1:8000/matches/SFC --data-binary "@SFC.txt"

curl-json-sfc:
	curl -i -X POST http://127.0.0.1:8000/matches/SFC --data-binary "@SFC.txt"
