#!/bin/bash
cd "$(dirname "$0")" || exit
source ./_setenv.sh
source ./venv/bin/activate
exec python client.py $@


