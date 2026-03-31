#!/bin/bash
cd "$(dirname "$0")" || exit
source ./.env/bin/activate
exec mypy ai8.py