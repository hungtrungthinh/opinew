# Create celery app based on flask app configurations
import datetime
from flask import current_app, url_for
from webapp import create_app, models, db
from providers import magento_api
from celery_async import make_celery
from config import Constants

app = current_app or create_app('db_prod')
this_celery = make_celery(app)


@this_celery.task()
def add_together(a, b):
    return a + b


@this_celery.task()
def delete(a, b):
    # used for testing failing tasks like division/0
    return a / b


@this_celery.task()
def send_email(*args, **kwargs):
    from async.email_sender import send_email

    send_email(*args, **kwargs)


@this_celery.task()
def create_shopify_shop(shopify_api, shop_id):
    shop = models.Shop.query.filter_by(id=shop_id).first()

    # Create webhooks
    shopify_api.create_webhook("products/create",
                               "%s%s" % (app.config.get('OPINEW_API_SERVER'),
                                         url_for('api.platform_shopify_create_product')))
    shopify_api.create_webhook("products/update",
                               "%s%s" % (app.config.get('OPINEW_API_SERVER'),
                                         url_for('api.platform_shopify_update_product')))
    shopify_api.create_webhook("products/delete",
                               "%s%s" % (app.config.get('OPINEW_API_SERVER'),
                                         url_for('api.platform_shopify_delete_product')))
    shopify_api.create_webhook("orders/create",
                               "%s%s" % (app.config.get('OPINEW_API_SERVER'),
                                         url_for('api.platform_shopify_create_order')))
    shopify_api.create_webhook("fulfillments/create",
                               "%s%s" % (app.config.get('OPINEW_API_SERVER'),
                                         url_for('api.platform_shopify_fulfill_order')))
    shopify_api.create_webhook("app/uninstalled",
                               "%s%s" % (app.config.get('OPINEW_API_SERVER'),
                                         url_for('api.platform_shopify_fulfill_order')))

    # Get shopify products
    shopify_products = shopify_api.get_products()

    # Import shop products
    for product_j in shopify_products:
        product_url = "https://%s/products/%s" % (shop.domain, product_j.get('handle', ''))
        product = models.Product(name=product_j.get('title', ''),
                                 shop=shop,
                                 platform_product_id=product_j.get('id', ''))
        product_url = models.ProductUrl(url=product_url)
        product.urls.append(product_url)
        db.session.add(product)
    db.session.commit()

    # Get shopify orders
    shopify_orders = shopify_api.get_orders()

    # Import shop orders
    for order_j in shopify_orders:
        platform_order_id = str(order_j.get('id', 0))
        existing_order = models.Order.query.filter_by(shop_id=shop_id, platform_order_id=platform_order_id).first()
        if existing_order:
            continue

        try:
            created_at_dt = datetime.datetime.strptime(order_j.get('created_at')[:-6], "%Y-%m-%dT%H:%M:%S")
        except:
            created_at_dt = datetime.datetime.utcnow()

        user_name = "%s %s" % (
            order_j.get('customer', {}).get('first_name'), order_j.get('customer', {}).get('last_name'))

        existing_user = models.User.get_by_email_no_exception(order_j.get('email'))
        if existing_user:
            order = models.Order(
            purchase_timestamp=created_at_dt,
            platform_order_id=platform_order_id,
            shop_id=shop.id,
            user=existing_user
            )
        else:
            user_legacy, _ = models.UserLegacy.get_or_create_by_email(email=order_j.get('email'), name=user_name)
            order = models.Order(
                purchase_timestamp=created_at_dt,
                platform_order_id=platform_order_id,
                shop_id=shop.id,
                user_legacy=user_legacy
            )
        if order_j.get('fulfillment_status'):
            order.status = Constants.ORDER_STATUS_SHIPPED
        if order_j.get('cancelled_at'):
            order.status = Constants.ORDER_STATUS_FAILED
        for product_j in order_j.get('line_items', []):
            product = models.Product.query.filter_by(platform_product_id=str(product_j.get('product_id'))).first()
            if product:
                order.products.append(product)
            else:
                variant = models.ProductVariant.query.filter_by(
                    platform_variant_id=str(product_j.get('variant_id'))).first()
                if not variant:
                    continue
                order.products.append(variant.product)
        db.session.add(order)
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
