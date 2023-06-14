#!/usr/bin/sh


python3 -m venv /tmp/m41.venv
. /tmp/m41.venv/bin/activate
python3 -m pip install -q -r requirements.txt
python3 -m unittest discover

