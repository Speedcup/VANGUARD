PACKAGE := src

NAME_CONTAINER := vanguard

.PHONY: start
start:
	uv run python -m $(PACKAGE).main

.PHONY: lint
lint:
	ruff check $(PACKAGE)

.PHONY: lint-fix
lint-fix:
	ruff check $(PACKAGE) --fix

.PHONY: format
format:
	ruff format $(PACKAGE)

.PHONY: docker-build
docker-build:
	docker build -t $(NAME_CONTAINER) .

.PHONY: seed
seed:
	uv run python -m $(PACKAGE).database.seeds
