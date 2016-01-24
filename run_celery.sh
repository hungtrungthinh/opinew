#!/usr/bin/env bash
source venv/bin/activate
celery -A async.tasks.this_celery worker -l info --statedb=~/celery_worker.state
