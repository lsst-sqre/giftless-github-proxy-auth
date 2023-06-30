.PHONY: update-deps
update-deps:
	pip install --upgrade pip-tools pip setuptools
	pip-compile --upgrade --resolver=backtracking --build-isolation \
	    --generate-hashes                                           \
	    --output-file requirements/main.txt requirements/main.in
	pip-compile --upgrade --resolver=backtracking --build-isolation \
	    --generate-hashes 				                \
	    --output-file requirements/dev.txt requirements/dev.in

.PHONY: init
init:
	pip install --editable .
	pip install --upgrade -r requirements/main.txt -r requirements/dev.txt
	rm -rf .tox
	pip install --upgrade pre-commit tox
	pre-commit install

.PHONY: update
update: update-deps init

.PHONY: run
run:
	tox -e=run

.PHONY: wheel
wheel:
	python3 -m build

.PHONY: docker
PACKAGE_NAME := giftless
REGISTRY := docker.io
OWNER := lsstsqre
TAG := ajt-dev
docker:
	docker build -t $(REGISTRY)/$(OWNER)/$(PACKAGE_NAME):$(TAG) .
