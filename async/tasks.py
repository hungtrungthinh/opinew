from flask import current_app
from webapp import create_app
from celery import Celery


def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery

app = current_app or create_app('dummy')
celery = make_celery(app)

@celery.task()
def add_together(a, b):
    return a + b

@celery.task()
def send_email(*args, **kwargs):
    from async.email_sender import send_email
    send_email(*args, **kwargs)
