import datetime
from flask import jsonify, session
from flask_wtf.csrf import generate_csrf
from flask.ext.security import login_user, current_user, login_required
from flask.ext.security.utils import verify_password
from flask.ext.restless import ProcessingException
from webapp import api_manager, models, db, csrf
from webapp.api import api
from webapp.common import get_post_payload, param_required, catch_exceptions, random_pwd
from webapp.exceptions import DbException
from config import Constants


def del_csrf(data, *args, **kwargs):
    if '_csrf_token' in data:
        del data['_csrf_token']

def auth_func(*args, **kwargs):
    if not current_user.is_authenticated():
        raise ProcessingException(description='Not authenticated!', code=401)


def req_shop_owner(*args, **kwargs):
    if not current_user.is_authenticated() or not current_user.has_role(Constants.SHOP_OWNER_ROLE):
        raise ProcessingException(description='Not authenticated!', code=401)


def pre_review_like_post(data, *args, **kwargs):
    review_id = data.get('review_id')
    if not review_id:
        raise ProcessingException(description='Review id requried!', code=401)
    review = models.Review.query.filter_by(id=review_id).first()
    if not review:
        raise ProcessingException(description='Review doesnt exist', code=401)
    review_like = models.ReviewLike.query.filter_by(review_id=review_id, user_id=current_user.id).first()
    if review_like:
        raise ProcessingException(description='Review already liked', code=401)
    data['user_id'] = current_user.id
    return data


def pre_create_review(data, *args, **kwargs):
    shop_id = data.get('shop_id')
    if shop_id:
        shop = models.Shop.query.filter_by(id=shop_id).first()
        if shop.owner == current_user:
            data['by_shop_owner'] = True
    order_id = data.get('order_id')
    if order_id:
        order_token = data.get('order_token')
        if not order_token:
            raise ProcessingException(description='Order token required', code=401)
        order = models.Order.query.filter_by(id=order_id).first()
        if not order:
            raise ProcessingException(description='No such order', code=401)
        if order.user and not order.user == current_user:
            raise ProcessingException(description='Not your order to review', code=401)
        if order.token == order_token:
            raise ProcessingException(description='Wrong order token', code=401)
        product_id = data.get('product_id')
        if not product_id:
            raise ProcessingException(description='Posting an order needs to have product id as well', code=401)
        product = models.Product.query.filter_by(id=product_id).first()
        if order and not product == order.product:
            raise ProcessingException(description='Product not in order', code=401)
        data['verified_review'] = True
        del data['order_id']
        del data['order_token']
    return data


def pre_create_order(data, *args, **kwargs):
    shop_id = data.get('shop_id')
    if not shop_id:
        raise ProcessingException(description='Shop id required', code=401)
    shop = models.Shop.query.filter_by(id=shop_id).first()
    if not shop.owner == current_user:
        raise ProcessingException(description='Not your shop', code=401)
    data['token'] = random_pwd(7)
    data['purchase_timestamp'] = str(datetime.datetime.utcnow())
    return data


def pre_create_product(data, *args, **kwargs):
    shop_id = data.get('shop_id')
    if not shop_id:
        raise ProcessingException(description='Shop id required', code=401)
    shop = models.Shop.query.filter_by(id=shop_id).first()
    if not shop.owner == current_user:
        raise ProcessingException(description='Not your shop', code=401)
    product_url = data.get('url')
    product_name = data.get('name')
    if not product_url or not product_name:
        raise ProcessingException(description='Product url and name required', code=401)
    product_exists = models.Product.query.filter_by(url=product_url).first()
    if product_exists:
        raise ProcessingException(description='Product with that url exists', code=401)
    shop_domain = shop.domain
    if not product_url.startswith(shop_domain):
        raise ProcessingException(description='Product url needs to start with the shop domain: %s' % shop.domain,
                                  code=401)
    return data


def pre_create_shop(data, *args, **kwargs):
    data['owner_id'] = current_user.id


def read_notification(instance_id, *args, **kwargs):
    notification = models.Notification.filter_by(id=instance_id).fist()
    if not notification or not notification.user == current_user:
        raise ProcessingException(description='Not your notification', code=401)


def is_shop_owned_by_user(instance_id, *args, **kwargs):
    shop = models.Shop.query.filter_by(id=instance_id).first()
    if not shop or not shop.owner == current_user:
        raise ProcessingException(description='Not your shop', code=401)


api_manager.create_api(models.Product,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['GET', 'POST', 'PATCH'],
                       preprocessors={
                           'POST': [del_csrf, req_shop_owner, pre_create_product],
                           'PATCH_SINGLE': [del_csrf, req_shop_owner]
                       }, )


# To query the reviews:
# http://flask-restless.readthedocs.org/en/latest/searchformat.html
# e.g. http://localhost:5000/api/v1/review?q={"order_by": [{"field": "created_ts", "direction":"desc"}], "offset":10}
api_manager.create_api(models.Review,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['GET', 'POST'],
                       preprocessors={
                           'POST': [del_csrf, auth_func, pre_create_review],
                           'PATCH_SINGLE': [del_csrf, auth_func]
                       },
                       exclude_columns=models.User.exclude_fields(),
                       validation_exceptions=[DbException])

api_manager.create_api(models.ReviewLike,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['POST', 'PATCH'],
                       preprocessors={
                           'POST': [del_csrf, auth_func, pre_review_like_post],
                           'PATCH_SINGLE': [del_csrf, auth_func]
                       },
                       exclude_columns=models.User.exclude_fields(),
                       validation_exceptions=[DbException])

api_manager.create_api(models.Order,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['GET', 'POST'],
                       preprocessors={
                           'GET_SINGLE': [auth_func, req_shop_owner],
                           'GET_MANY': [del_csrf, auth_func, req_shop_owner],
                           'POST': [del_csrf, req_shop_owner, pre_create_order],
                       }, )

api_manager.create_api(models.User,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['GET'],
                       include_columns=models.User.include_own_fields(),
                       validation_exceptions=[DbException])

api_manager.create_api(models.Notification,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['GET'],
                       preprocessors={
                           'GET_SINGLE': [auth_func],
                           'GET_MANY': [auth_func],
                           'PATCH_SINGLE': [del_csrf, auth_func, read_notification]
                       }, )

api_manager.create_api(models.Shop,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['POST', 'PATCH'],
                       preprocessors={
                           'POST': [del_csrf, req_shop_owner, pre_create_shop],
                           'PATCH_SINGLE': [del_csrf, req_shop_owner, is_shop_owned_by_user]
                       },
                       validation_exceptions=[DbException])

@login_required
@api.route('/token')
def token():
    return jsonify({'token': generate_csrf()})


@api.route('/auth', methods=['POST'])
@csrf.exempt
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
    user = models.User.query.filter_by(email=email).first()
    if not user:
        raise DbException('unknown user', 400)
    if not verify_password(password, user.password):
        raise DbException('invalid password', 400)
    login_user(user)
    return jsonify({})



from webapp.api.webhooks import shopify


# from flask import jsonify, request
# from flask.ext.security import login_user, login_required, current_user
# from webapp import db, review_photos
# from webapp.common import get_post_payload, param_required, build_created_response, reviewer_required, verify_webhook, \
#     shop_owner_required, catch_exceptions
# from webapp.models import User, Product, ShopProduct, Review, Order, Shop, Notification, ProductReview
# from webapp.exceptions import ParamException
#
# TODO: Done
# @api.route('/products/<int:product_id>')
# @catch_exceptions
# def get_product(product_id):
#     product = Product.get_by_id(product_id)
#     return jsonify(product.serialize())
#
# TODO: Done
# @api.route('/reviews')
# @catch_exceptions
# def get_latest_reviews():
#     """
#     Fetch 10 most recent reviews
#     """
#     reviews = Review.get_latest(10)
#     return jsonify({'reviews': [r.serialize_with_product() for r in reviews]}), 200
#
# TODO: Done
# @api.route('/orders/<int:order_id>')
# @shop_owner_required
# @login_required
# @catch_exceptions
# def get_order(order_id):
#     order = Order.get_by_id(order_id)
#     order.is_for_user(current_user)
#     return jsonify(order.serialize())
#
# TODO: Done
# @api.route('/notifications')
# @login_required
# @catch_exceptions
# def get_notifications():
#     notifications = Notification.get_for_user(current_user)
#     return jsonify({'notifications': [notification.serialize() for notification in notifications]}), 200
#
# TODO: Done
# @api.route('/reviews/<int:review_id>')
# @catch_exceptions
# def get_review(review_id):
#     review = Product.get_by_id(review_id)
#     return jsonify(review.serialize())
#
#
# @api.route('/reviews/<int:review_id>/approve', methods=['PATCH'])
# @shop_owner_required
# @login_required
# @catch_exceptions
# def approve_product_review(review_id):
#     shop_review = ProductReview.get_by_review_id(review_id)
#
#     payload = get_post_payload()
#     action = param_required('action', payload)
#
#     if action == 'approve':
#         shop_review.approve()
#     elif action == 'disapprove':
#         shop_review.disapprove()
#     else:
#         raise ParamException('action can be one of approve|disapprove', 400)
#     return jsonify(shop_review.serialize()), 200
#
#
# @api.route('/shop/<int:shop_id>/products/<int:product_id>/reviews', methods=['POST'])
# @reviewer_required
# @login_required
# @catch_exceptions
# def add_product_review(shop_id, product_id):
#     payload = get_post_payload()
#     Shop.exists(shop_id)
#
#     order = Order.get_by_shop_product_user(shop_id, product_id, current_user.id)
#     order.review_not_exists()
#
#     product = Product.get_by_id(product_id)
#
#     body = payload.get('body', None)
#     photo_url = ''
#     if 'photo' in request.files:
#         photo_url = review_photos.save(request.files['photo'])
#     tag_ids = request.values.getlist('tag_id')
#
#     if not body and not tag_ids and not photo_url:
#         raise ParamException('At least one of body, photo or tags need to be provided.', 400)
#
#     review = product.add_review(order=order, body=body, photo_url=photo_url, tag_ids=tag_ids, shop_id=shop_id)
#     return build_created_response('.get_review', review_id=review.id)
#
#
# @api.route('/notifications/<int:notification_id>', methods=['PATCH'])
# @login_required
# @catch_exceptions
# def update_notification(notification_id):
#     notification = Notification.get_by_id(notification_id)
#     notification.is_for_user(current_user)
#
#     payload = get_post_payload()
#     action = param_required('action', payload)
#
#     if action == 'read':
#         notification.read()
#     else:
#         raise ParamException('action can be one of read', 400)
#     return jsonify(notification.serialize()), 200
