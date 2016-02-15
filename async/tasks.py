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
def send_email(*args, **kwargs):
    from async.email_sender import send_email

    send_email(*args, **kwargs)


@this_celery.task()
def create_shopify_shop(shopify_api, shop_id):
    shop = models.Shop.query.filter_by(id=shop_id).first()

    # Create webhooks
    shopify_api.create_webhook("products/create",
                               "%s%s" % (app.config.get('OPINEW_API_SERVER'),
                                         "/api/v1/platform/shopify/products/create"))
    shopify_api.create_webhook("products/update",
                               "%s%s" % (app.config.get('OPINEW_API_SERVER'),
                                         "/api/v1/platform/shopify/products/update"))
    shopify_api.create_webhook("products/delete",
                               "%s%s" % (app.config.get('OPINEW_API_SERVER'),
                                         "/api/v1/platform/shopify/products/delete"))
    shopify_api.create_webhook("orders/create",
                               "%s%s" % (app.config.get('OPINEW_API_SERVER'),
                                         "/api/v1/platform/shopify/orders/create"))
    shopify_api.create_webhook("fulfillments/create",
                               "%s%s" % (app.config.get('OPINEW_API_SERVER'),
                                         "/api/v1/platform/shopify/orders/fulfill"))
    shopify_api.create_webhook("app/uninstalled",
                               "%s%s" % (app.config.get('OPINEW_API_SERVER'),
                                         "/api/v1/platform/shopify/app/uninstalled"))

    # Get shopify products
    shopify_products_count = shopify_api.get_products_count()
    total_pages = shopify_products_count / Constants.SHOPIFY_MAX_PRODUCTS_PER_PAGE + 1
    for page in range(1, total_pages + 1):
        shopify_products = shopify_api.get_products(page=page)

        # Import shop products
        for product_j in shopify_products:
            product = models.Product(name=product_j.get('title', ''),
                                     shop=shop,
                                     platform_product_id=product_j.get('id', ''))
            db.session.add(product)
            for variant_j in product_j.get('variants', []):
                var = models.ProductVariant(product=product,
                                            platform_variant_id=str(variant_j.get('id', '')))
                db.session.add(var)
    db.session.commit()

    shopify_orders_count = shopify_api.get_orders_count()
    total_pages = shopify_orders_count / Constants.SHOPIFY_MAX_ORDERS_PER_PAGE + 1
    for page in range(1, total_pages + 1):
        # Get shopify orders
        shopify_orders = shopify_api.get_orders(page=page)

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

            order = models.Order(
                purchase_timestamp=created_at_dt,
                platform_order_id=platform_order_id,
                shop_id=shop.id
                )

            existing_user = models.User.get_by_email_no_exception(order_j.get('email'))
            if existing_user:
                order.user = existing_user
            else:
                user_name = "%s %s" % (order_j.get('customer', {}).get('first_name'),
                                       order_j.get('customer', {}).get('last_name')
                                       )
                user_legacy, _ = models.UserLegacy.get_or_create_by_email(email=order_j.get('email'), name=user_name)
                order.user_legacy = user_legacy

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
