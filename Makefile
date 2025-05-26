PKG_NAME=domos-pmea
CONFIG_FILE=config.yml
REDIS_CONTAINER_NAME=pmea-redis
TEST_LOG_LEVEL=INFO

.PHONY: venv
venv:
	@uv venv

.PHONY: install-dev
install-dev: venv
	@uv pip install -e .

.PHONY: run
run: install-dev
	@uv run $(PKG_NAME) --config $(CONFIG_FILE)

.PHONY: test
test:
	@uv run pytest -s -o log_cli_level=$(TEST_LOG_LEVEL) $(PYTEST_ARGS)

.PHONY: clean.redis
clean.redis:
	@docker exec $(REDIS_CONTAINER_NAME) redis-cli 'FLUSHDB'

.PHONY: clean.files
clean.files:
	@rm -rf .venv __pycache__ .pytest_cache .mypy_cache dist build *.egg-info

.PHONY: clean
clean: clean.redis clean.files
	@echo 'Removed all temp files and Redis data'

