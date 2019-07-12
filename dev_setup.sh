#!/bin/sh

virtualenv -p python2.7 venv
venv/bin/pip install -r requirements.txt pytest
