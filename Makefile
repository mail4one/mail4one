

shell: 
	MYPYPATH=`pipenv --venv`/lib/python3.11/site-packages pipenv shell

test:
	pipenv run python -m unittest mail4one/*test.py
