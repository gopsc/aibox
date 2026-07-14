#!/bin/bash
cd "$(dirname "$0")" || exit
source ./_setenv.sh
source ./.env/bin/activate
export PATH=${PATH}:~/.aibox/skills
exec python main.py $@


