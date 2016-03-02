# Create celery app based on flask app configurations
import datetime
from flask import current_app, g
from webapp import create_app, models, db
from providers import magento_api
from celery_async import make_celery
from config import Constants
from providers.shopify_api import OpinewShopifyFacade
from providers import database

app = current_app or create_app('db_prod')

this_celery = make_celery(app)


@this_celery.task()
def send_email(*args, **kwargs):
    from async.email_sender import send_email

    send_email(*args, **kwargs)


@this_celery.task()
def create_shopify_shop(shop_id):
    g.db = database.OpinewSQLAlchemyFacade()
    shop = g.db.Shop.get_by_id(shop_id)
    opinew_shopify = OpinewShopifyFacade(shop=shop)
    opinew_shopify.create_webhooks()
    opinew_shopify.import_products()
    opinew_shopify.import_orders()


@this_celery.task()
def create_customer_account(user_id, plan_name):
    # 1. Flushing only doesn't work because in production, flush doesn't end the transation. Though it works in test.
    # 2. Instantiating a session with session maker doesn't work, because
    #    you can't add the same object to different sessions (Customer already exists in session 2, this is 3)
    # 3. Original code doesn't work in test, because this task executes immediately and a commit to db clears
    #    the session. Therefore when we return to models.post_registration_handler which returns to flask_security
    #    registrable:40, the use is no longer in the session.
    user = models.User.query.filter_by(id=user_id).first()
    plan_name = plan_name or Constants.PLAN_NAME_SIMPLE
    plan = models.Plan.query.filter_by(name=plan_name).first()
    customer = models.Customer(user=user).create()
    subscription = models.Subscription(customer=customer, plan=plan).create()
    db.session.add(customer)
    db.session.add(subscription)
    db.session.commit()


@this_celery.task()
def update_orders():
    magento_platform = models.Platform.query.filter_by(name="magento").first()
    shops = models.Shop.query.filter_by(platform=magento_platform).all()
    for shop in shops:
        magento_api.init(shop)


@this_celery.task()
def notify_for_review(order_id, *args, **kwargs):
    order = models.Order.query.filter_by(id=order_id).first()
    if order:
        order.notify()


@this_celery.task
def task_wrapper(task, task_instance_id, **kwargs):
    task(**kwargs)
    task_instance = models.Task.query.filter_by(id=task_instance_id).first()
    if task_instance:
        task_instance.status = 'SUCCESS'
        db.session.add(task_instance)
        db.session.commit()
