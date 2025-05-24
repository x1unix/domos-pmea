PKG_NAME=domos-pmea
CONFIG_FILE=config.yml

.PHONY: venv
venv:
	@uv venv

.PHONY: install-dev
install-dev: venv
	@uv pip install -e .

.PHONY: run
run: install-dev
	@uv run $(PKG_NAME) --config $(CONFIG_FILE)

.PHONY: clean
clean:
	@rm -rf .venv __pycache__ .pytest_cache .mypy_cache dist build *.egg-info