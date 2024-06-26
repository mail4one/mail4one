# Needs python3 >= 3.9, sed, git for build
mail4one.pyz: requirements.txt mail4one/*py
	python3 -m pip install -r requirements.txt --no-compile --target build
	cp -r mail4one/ build/
	sed -i "s/DEVELOMENT/$(shell scripts/get_version.sh)/" build/mail4one/version.py
	find build -name "*.pyi" -o -name "py.typed" | xargs -I typefile rm typefile
	rm -rf build/bin build/aiosmtpd/{docs,tests,qa}
	rm -rf build/mail4one/__pycache__
	rm -rf build/*.dist-info
	python3 -m zipapp \
		--output mail4one.pyz \
		--python "/usr/bin/env python3" \
		--main mail4one.server:main \
		--compress build

.PHONY: build
build: clean mail4one.pyz

.PHONY: test
test: mail4one.pyz
	PYTHONPATH=mail4one.pyz python3 -m unittest discover

.PHONY: clean
clean:
	rm -rf build
	rm -rf mail4one.pyz

.PHONY: docker-tests
docker-tests:
	docker run --pull=always -v `pwd`:/app -w /app --rm python:3.11-alpine sh scripts/runtests.sh
	docker run --pull=always -v `pwd`:/app -w /app --rm python:3.10-alpine sh scripts/runtests.sh
	docker run --pull=always -v `pwd`:/app -w /app --rm python:3.12        sh scripts/runtests.sh
	docker run --pull=always -v `pwd`:/app -w /app --rm python:3.11        sh scripts/runtests.sh
	docker run --pull=always -v `pwd`:/app -w /app --rm python:3.10        sh scripts/runtests.sh
	docker run --pull=always -v `pwd`:/app -w /app --rm python:3.9         sh scripts/runtests.sh

# ============================================================================
# Below targets for devs. Need pipenv, black installed

requirements.txt: Pipfile.lock
	pipenv requirements > requirements.txt

.PHONY: format
format:
	black mail4one/*py tests/*py

.PHONY: build-dev
build-dev: requirements.txt build

.PHONY: setup
setup:
	pipenv install

.PHONY: cleanup
cleanup:
	pipenv --rm

.PHONY: update
update:
	rm requirements.txt Pipfile.lock
	pipenv update
	pipenv requirements > requirements.txt

.PHONY: shell
shell:
	MYPYPATH=$(shell ls -d `pipenv --venv`/lib/python3*/site-packages) pipenv shell
	
.PHONY: dev-test
dev-test:
	pipenv run python -m unittest discover
