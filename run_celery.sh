#!/usr/bin/env bash
source venv/bin/activate
celery -A async.tasks.this_celery worker -l info --statedb=/home/opinew_server/celery_worker.state