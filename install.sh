#!/usr/bin/env bash
# eisy's system Python can report pipenv/setuptools conflicts that make
# pip exit 1 even after this plugin's packages install successfully.
# PG3 treats a non-zero install.sh as a failed plugin install (HTTP 500).
pip3 install -r requirements.txt --user
python3 -c "import udi_interface, yaml, paho.mqtt"
