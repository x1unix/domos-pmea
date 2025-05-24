PKG_NAME=domos-pmea

.PHONY: venv
venv:
	@uv venv

.PHONY: install-dev
install-dev: venv
	@uv pip install -e .

.PHONY: run
run: install-dev
	@uv run $(PKG_NAME)

.PHONY: clean
clean:
	@rm -rf .venv __pycache__ .pytest_cache .mypy_cache dist build *.egg-info