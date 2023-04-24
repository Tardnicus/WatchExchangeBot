#!/usr/bin/env sh

# Fail script on any error
set -e

# Update database to the newest version
# Should happen on startup in case models need migration due to a container update
python -m alembic upgrade head

# exec this process to avoid spawning child processes
exec python ./wemb/main.py
