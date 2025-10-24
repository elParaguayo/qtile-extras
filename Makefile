.DEFAULT_GOAL := help

ifeq ($(QTILE_CI_PYTHON),)
UV_PYTHON_ARG =
else
UV_PYTHON_ARG = --python=$(QTILE_CI_PYTHON)
endif

TEST_RUNNER = python3 -m pytest

QTILE_PATH := ".venv/lib/python3.11/site-packages"

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[1m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: check
check: ## Run the test suite on the latest python
	uv sync $(UV_PYTHON_ARG) --all-extras
	uv pip install --config-settings backend=wayland "git+https://github.com/qtile/qtile.git#egg=qtile[wayland]" --no-build-isolation
	uv run $(UV_PYTHON_ARG) $(TEST_RUNNER) --backend=x11 --backend=wayland

.PHONY: check-packaging
check-packaging:  ## Check that the packaging is sane
	uv run $(UV_PYTHON_ARG) check-manifest
	uv run $(UV_PYTHON_ARG) python3 -m build --sdist .
	uv run $(UV_PYTHON_ARG) twine check dist/*

.PHONY: check-decorations
check-decorations: ## Check decorations are rendered correctly
	-rm -rf decoration_images
	mkdir decoration_images
	uv sync $(UV_PYTHON_ARG) --all-extras
	uv pip install --config-settings backend=wayland "git+https://github.com/qtile/qtile.git#egg=qtile[wayland]" --no-build-isolation
	uv run $(UV_PYTHON_ARG) $(TEST_RUNNER) --backend=x11 --backend=wayland -k "test_decoration_output" --generate-ci

.PHONY: lint
lint: ## Check the source code
	pre-commit run -a

.PHONY: clean
clean: ## Clean generated files
	-rm -rf dist qtile_extras.egg-info docs/_build build/ .mypy_cache/ .pytest_cache/ .eggs/

.PHONY: distclean
distclean: clean ## Clean generated files and virtual environment
	-rm -rf .venv