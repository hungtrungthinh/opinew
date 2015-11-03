from async.celery_async import this_celery


@this_celery.task()
def add_together(a, b):
    return a + b


@this_celery.task()
def send_email(*args, **kwargs):
    from async.email_sender import send_email

    send_email(*args, **kwargs)


@this_celery.task()
def update_orders():
    pass
    # 0. Get all the shops
    # 1. Query magento for orders for this shop
    # 2. Get orders for this shop in our db
    # 3. Compare if any orders need to be created or updated
    # 4. If the order needs to be updated - schedule order_delivered


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
