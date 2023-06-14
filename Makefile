

shell: 
	MYPYPATH=`pipenv --venv`/lib/python3.11/site-packages pipenv shell

test:
	pipenv run python -m unittest discover

build: clean
	pipenv run python -m pip install -r <(pipenv requirements ) --target build
	cp -r mail4one/ build/
	pipenv run python -m compileall build/mail4one -f
	pipenv run python -m zipapp \
		--output mail4one.pyz \
		--python "/usr/bin/env python3" \
		--main mail4one.server:main \
		--compress build

clean:
	rm -rf build
	rm -rf mail4one.pyz
