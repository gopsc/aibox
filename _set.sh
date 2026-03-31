#!/bin/bash
cd "$(dirname "$0")" || exit
python3 -m venv .env
source .env/bin/activate
pip install -r requirements.txt -i https://pypi.org/simple

