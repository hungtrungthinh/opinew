# Create celery app based on flask app configurations
from flask import current_app
from webapp import create_app
from webapp import models
from providers import magento_api
from celery_async import make_celery

app = current_app or create_app('db_prod')
this_celery = make_celery(app)

@this_celery.task()
def add_together(a, b):
    return a + b


@this_celery.task()
def send_email(*args, **kwargs):
    from async.email_sender import send_email

    send_email(*args, **kwargs)


@this_celery.task()
def update_orders():
    magento_platform = models.Platform.query.filter_by(name="magento").first()
    shops = models.Shop.query.filter_by(platform=magento_platform).all()
    for shop in shops:
        magento_api.init(shop)


@this_celery.task()
def update_products():
    pass


@this_celery.task()
def order_delivered():
    pass
    # 1. Schedule notify for review


@this_celery.task()
def notify_for_review():
    pass
