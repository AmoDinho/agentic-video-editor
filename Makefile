.PHONY: up up-fast down doctor override sidecar test

override:
	python3 deploy/media_mounts.py .

up: override
	docker compose up --build

up-fast: override
	docker compose up --build -d
	@echo "Starting native GPU sidecar on :8077 (mlx-whisper + CLIP)."
	uv run --python 3.11 python -m ave.sidecar || python3 -m ave.sidecar

down:
	docker compose down

doctor:
	python3 deploy/doctor.py

sidecar:
	python3 -m ave.sidecar

test:
	python3 -m pytest -q
