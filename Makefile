test:
	PYTHONPATH=src pytest

lint:
	ruff check src

format:
	ruff format src

install:
	pip install pytest pytest-cov ruff