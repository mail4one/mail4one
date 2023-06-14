

shell: 
	MYPYPATH=`pipenv --venv`/lib/python3.11/site-packages pipenv shell

test:
	pipenv run python -m unittest discover

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
