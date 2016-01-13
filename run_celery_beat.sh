#!/usr/bin/env bash
source venv/bin/activate
celery -A async.tasks.this_celery beat -l info