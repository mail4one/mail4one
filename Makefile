# Needs python3 >= 3.9, sed, git for build
build: clean
	python3 -m pip install -r requirements.txt --no-compile --target build
	cp -r mail4one/ build/
	sed -i "s/DEVELOMENT/$(shell scripts/get_version.sh)/" build/mail4one/version.py
	rm -rf build/mail4one/__pycache__
	rm -rf build/*.dist-info
	python3 -m zipapp \
		--output mail4one.pyz \
		--python "/usr/bin/env python3" \
		--main mail4one.server:main \
		--compress build

clean:
	rm -rf build
	rm -rf mail4one.pyz

docker-tests:
	docker run --pull=always -v `pwd`:/app -w /app --rm python:3.11-alpine sh scripts/runtests.sh
	docker run --pull=always -v `pwd`:/app -w /app --rm python:3.10-alpine sh scripts/runtests.sh
	docker run --pull=always -v `pwd`:/app -w /app --rm python:3.11        sh scripts/runtests.sh
	docker run --pull=always -v `pwd`:/app -w /app --rm python:3.10        sh scripts/runtests.sh
	docker run --pull=always -v `pwd`:/app -w /app --rm python:3.9         sh scripts/runtests.sh

# ============================================================================

requirements.txt: Pipfile.lock
	pipenv requirements > requirements.txt

format:
	black mail4one/*py

build-dev: requirements.txt build

setup:
	pipenv install

cleanup:
	pipenv --rm

shell:
	MYPYPATH=`pipenv --venv`/lib/python3.11/site-packages pipenv shell
	
test:
	pipenv run python -m unittest discover
