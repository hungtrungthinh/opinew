#!/usr/bin/env bash
source venv/bin/activate
flower -A async.tasks.celery --broker=amqp://guest:guest@localhost:5672//