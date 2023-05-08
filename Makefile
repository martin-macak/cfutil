build:
	poetry build

install: build
	pip install $$(find dist -name "*.whl") --force-reinstall