.DEFAULT_GOAL := check


pip_params = --disable-pip-version-check --upgrade --upgrade-strategy=eager


.PHONY: upgrade-pip
upgrade-pip:
	pip install $(pip_params) pip wheel


.PHONY: install
install: upgrade-pip
	pip install --disable-pip-version-check '.'


.PHONY: install-dev
install-dev: upgrade-pip
	pip install $(pip_params) -r requirements-dev.txt
	pip install $(pip_params) --editable '.'


.PHONY: uninstall
uninstall:
	pip uninstall -y yappy


.PHONY: mypy
mypy:
	mypy yappy


.PHONY: format
format:
	isort yappy tests
	black yappy tests


.PHONY: isort
isort:
	isort --check --diff yappy tests


.PHONY: black
black:
	black --check --diff yappy tests


.PHONY: flake8
flake8:
	flake8 --max-complexity 10 --ignore E203 yappy tests


.PHONY: check
check: mypy isort black flake8


.PHONY: test
test:
	pytest


.PHONY: coverage
coverage:
	coverage run -m pytest


.PHONY: report
report:
	coverage report -m --skip-covered


.PHONY: build
build:
	python -m build


.PHONY: publish
publish:
	python -m twine check dist/*
	python -m twine upload --verbose dist/*
