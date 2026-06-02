.PHONY: dev migrate revision seed test lint

dev:
	uvicorn app.main:app --reload

migrate:
	alembic upgrade head

revision:
	alembic revision --autogenerate -m "auto"

seed:
	python -m app.scripts.seed

test:
	pytest -v --asyncio-mode=strict

lint:
	black app tests
	isort app tests
	flake8 app tests
