PKG_NAME=domos-pmea
CONFIG_FILE=config.yml
REDIS_CONTAINER_NAME=pmea-redis

.PHONY: venv
venv:
	@uv venv

.PHONY: install-dev
install-dev: venv
	@uv pip install -e .

.PHONY: run
run: install-dev
	@uv run $(PKG_NAME) --config $(CONFIG_FILE)

.PHONY: clean.redis
clean.redis:
	@docker exec $(REDIS_CONTAINER_NAME) redis-cli 'FLUSHDB'

.PHONY: clean.files
clean.files:
	@rm -rf .venv __pycache__ .pytest_cache .mypy_cache dist build *.egg-info

.PHONY: clean
clean: clean.redis clean.files
	@echo 'Removed all temp files and Redis data'

