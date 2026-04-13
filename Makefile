# Lint code (ruff + pyrefly; pyright available as "uv run pyright src" if needed)
lint:
	uv run ruff check src
	uv run pyrefly check src

# Format code
format:
	uv run ruff check --fix --unsafe-fixes src
	uv run ruff format src

install:
	uv sync --frozen --no-dev

installdev:
	uv sync --all-extras