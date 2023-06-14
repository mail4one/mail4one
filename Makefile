

shell: 
	MYPYPATH=`pipenv --venv`/lib/python3.11/site-packages pipenv shell

test:
	pipenv run python -m unittest discover

docker-tests:
	docker run --pull=always -v `pwd`:/app -w /app --rm -it python:3.11-alpine sh runtests.sh
	docker run --pull=always -v `pwd`:/app -w /app --rm -it python:3.10-alpine sh runtests.sh
	docker run --pull=always -v `pwd`:/app -w /app --rm -it python:3.11 sh runtests.sh
	docker run --pull=always -v `pwd`:/app -w /app --rm -it python:3.10 sh runtests.sh

requirements.txt: Pipfile.lock
	pipenv requirements > requirements.txt

build: clean requirements.txt
	python3 -m pip install -r requirements.txt --target build
	cp -r mail4one/ build/
	python3 -m compileall build/mail4one -f
	rm -rf build/*.dist-info
	python3 -m zipapp \
		--output mail4one.pyz \
		--python "/usr/bin/env python3" \
		--main mail4one.server:main \
		--compress build

clean:
	rm -rf build
	rm -rf mail4one.pyz
