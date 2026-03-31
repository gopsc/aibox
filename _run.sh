#!/bin/bash
cd "$(dirname "$0")" || exit
source ./_setenv.sh
source ./.env/bin/activate
exec python ai35.py $@


