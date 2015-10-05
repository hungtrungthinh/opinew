from flask import jsonify, request
from flask.ext.login import login_user, login_required, current_user
from webapp import db, review_photos
from webapp.api import api
from webapp.common import get_post_payload, param_required, build_created_response, reviewer_required, verify_webhook, \
    shop_owner_required, catch_exceptions
from webapp.models import User, Product, ShopProduct, Review, Order, Shop, Notification, ShopReview
from webapp.exceptions import ParamException, DbException


@api.route('/authenticate', methods=['POST'])
@catch_exceptions
def authenticate():
    """
    Authenticate user
    email: valid, registered email address
    password: valid password for email
    """
    payload = get_post_payload()
    email = param_required('email', payload)
    password = param_required('password', payload)
    user = User.get_by_email(email)
    user.validate_password(password)
    login_user(user)
    return jsonify({}), 200


@api.route('/products/<int:product_id>')
@catch_exceptions
def get_product(product_id):
    product = Product.get_by_id(product_id)
    return jsonify(product.serialize())


@api.route('/products/create', methods=['POST'])
@catch_exceptions
@verify_webhook
def create_product():
    """
    Currently this works with the Shopify API
    From Webhook - create product
    "topic": "products\/create"
    """
    payload = get_post_payload()

    shopify_shop_domain = request.headers.get('X-Shopify-Shop-Domain')
    shop = Shop.get_by_shop_domain(shopify_shop_domain)

    platform_product_id = payload.get('id')
    product_title = payload.get('title')

    product = Product(label=product_title)

    shop_product = ShopProduct(product=product, shop=shop, platform_product_id=platform_product_id)
    db.session.add(shop_product)
    db.session.commit()
    return build_created_response('.get_product', product_id=product.id)


@api.route('/products/update', methods=['POST'])
@verify_webhook
@catch_exceptions
def update_product():
    """
    Currently this works with the Shopify API
    From Webhook - update product
    "topic": "products\/update"
    """
    payload = get_post_payload()

    platform_product_id = payload.get('id')
    product_title = payload.get('title')

    shop_product = ShopProduct.get_by_platform_product_id(platform_product_id)
    product = shop_product.product
    product.label = product_title

    db.session.add(product)
    db.session.commit()
    return jsonify({}), 200


@api.route('/products/delete', methods=['POST'])
@verify_webhook
@catch_exceptions
def delete_product():
    """
    Currently this works with the Shopify API
    From Webhook - update product
    "topic": "products\/delete"
    """
    payload = get_post_payload()

    platform_product_id = payload.get('id')

    shop_product = ShopProduct.get_by_platform_product_id(platform_product_id)
    db.session.delete(shop_product)
    db.session.commit()
    return jsonify({}), 200


@api.route('/reviews')
@catch_exceptions
def get_latest_reviews():
    """
    Fetch 10 most recent reviews
    """
    reviews = Review.get_latest(10)
    return jsonify({'reviews': [r.serialize_with_product() for r in reviews]}), 200


@api.route('/orders/<int:order_id>')
@shop_owner_required
@login_required
@catch_exceptions
def get_order(order_id):
    order = Order.get_by_id(order_id)
    order.is_for_user(current_user)
    return jsonify(order.serialize())


@api.route('/orders/create', methods=['POST'])
@verify_webhook
@catch_exceptions
def create_order():
    payload = get_post_payload()

    shop_domain = request.headers.get('X-Shopify-Shop-Domain')
    shop = Shop.get_by_shop_domain(shop_domain)

    customer_email = payload.get('customer', {}).get('email')
    customer = User.get_or_create_by_email(customer_email)

    platform_order_id = payload.get('id')

    order = Order(platform_order_id=platform_order_id, user=customer, shop=shop)

    line_items = payload.get('line_items', [])
    for line_item in line_items:
        platform_product_id = line_item.get('product_id')
        shop_product = ShopProduct.get_by_platform_product_id(platform_product_id)
        product = shop_product.product
        order.products.append(product)

    db.session.add(order)
    db.session.commit()
    return build_created_response('.get_order', order_id=order.id)


@api.route('/orders/fulfill', methods=['POST'])
@verify_webhook
@catch_exceptions
def fulfill_order():
    payload = get_post_payload()
    platform_order_id = payload.get('order_id')

    order = Order.get_by_platform_order_id(platform_order_id)
    delivery_tracking_number = payload.get('tracking_number')
    order.ship(delivery_tracking_number)

    db.session.add(order)
    db.session.commit()
    return jsonify({}), 200


@api.route('/reviews/<int:review_id>')
@catch_exceptions
def get_review(review_id):
    review = Product.get_by_id(review_id)
    return jsonify(review.serialize())


@api.route('/reviews/<int:review_id>/approve', methods=['PATCH'])
@shop_owner_required
@login_required
@catch_exceptions
def approve_product_review(review_id):
    shop_review = ShopReview.get_by_review_id(review_id)

    payload = get_post_payload()
    action = param_required('action', payload)

    if action == 'approve':
        shop_review.approve()
    elif action == 'disapprove':
        shop_review.disapprove()
    else:
        raise ParamException('action can be one of approve|disapprove', 400)
    return jsonify(shop_review.serialize()), 200


@api.route('/shop/<int:shop_id>/products/<int:product_id>/reviews', methods=['POST'])
@reviewer_required
@login_required
@catch_exceptions
def add_product_review(shop_id, product_id):
    payload = get_post_payload()
    Shop.exists(shop_id)

    order = Order.get_by_shop_product_user(shop_id, product_id, current_user.id)
    order.review_not_exists()

    product = Product.get_by_id(product_id)

    body = payload.get('body', None)
    photo_url = ''
    if 'photo' in request.files:
        photo_url = review_photos.save(request.files['photo'])
    tag_ids = request.values.getlist('tag_id')

    if not body and not tag_ids and not photo_url:
        raise ParamException('At least one of body, photo or tags need to be provided.', 400)

    review = product.add_review(order=order, body=body, photo_url=photo_url, tag_ids=tag_ids)
    return build_created_response('.get_review', review_id=review.id)


@api.route('/notifications')
@login_required
@catch_exceptions
def get_notifications():
    notifications = Notification.get_for_user(current_user)
    return jsonify({'notifications': [notification.serialize() for notification in notifications]}), 200


@api.route('/notifications/<int:notification_id>', methods=['PATCH'])
@login_required
@catch_exceptions
def update_notification(notification_id):
    notification = Notification.get_by_id(notification_id)
    notification.is_for_user(current_user)

    payload = get_post_payload()
    action = param_required('action', payload)

    if action == 'read':
        notification.read()
    else:
        raise ParamException('action can be one of read', 400)
    return jsonify(notification.serialize()), 200
