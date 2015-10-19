from flask import jsonify, url_for
from flask.ext.security import login_user, current_user
from flask.ext.security.utils import verify_password
from flask.ext.restless import ProcessingException
from webapp import api_manager, models, db
from webapp.api import api
from webapp.common import get_post_payload, param_required, catch_exceptions
from webapp.exceptions import DbException
from config import Constants


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

def pre_create_review(data, *args, **kwargs):
    shop_id = data.get('shop_id')
    if shop_id:
        shop = models.Shop.query.filter_by(id=shop_id).first()
        if shop.owner == current_user:
            data['by_shop_owner'] = True
    order_id = data.get('order_id')
    order_token = data.get('order_token')
    if order_id and order_token:
        order = models.Order.query.filter_by(id=order_id).first()
        if not order:
            raise ProcessingException(description='No such order', code=401)
        if not order.user == current_user:
            raise ProcessingException(description='Not your order to review', code=401)
        shop_product_id = data.get('shop_product_id')
        if not shop_product_id:
            raise ProcessingException(description='Posting an order needs to have product id as well', code=401)
        shop_product = models.ShopProduct.query.filter_by(id=shop_product_id).first()
        if shop_product not in order.shop_products:
            raise ProcessingException(description='Product not in order', code=401)
        if not order.token == order_token:
            raise ProcessingException(description='Wrong order token', code=401)
        data['verified_review'] = True
        del data['order_id']
        del data['order_token']
    return data


def post_create_review(result, *args, **kwargs):
    shop_product_id = result.get('shop_product_id')
    review_id = result.get('id')
    review = models.Review.query.filter_by(id=review_id).first()
    shop_product_review = models.ShopProductReview(shop_product_id=shop_product_id, review_id=review_id)
    db.session.add(shop_product_review)
    db.session.commit()
    shop_owner = shop_product_review.shop_product.shop.owner
    notification = models.Notification(user=shop_owner,
                                       content='You received a new review about <b>%s</b>. <br>'
                                               'Click here to allow or deny display on plugin' % review.shop_product.product.name,
                                       url=url_for('client.view_review', review_id=review_id))
    db.session.add(notification)
    db.session.commit()


def read_notification(notification_id, *args, **kwargs):
    notification = models.Notification.get_by_id(notification_id)
    if not notification or not notification.user == current_user:
        raise ProcessingException(description='Not your notification', code=401)


def is_shop_owned_by_user(shop_id, *args, **kwargs):
    shop = models.Shop.query.filter(id=shop_id).first()
    if not shop or not shop.owner == current_user:
        raise ProcessingException(description='Not your shop', code=401)


api_manager.create_api(models.Product,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['GET'])

api_manager.create_api(models.Review,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['GET', 'POST'],
                       preprocessors={
                           'POST': [auth_func, pre_create_review],
                           'PATCH_SINGLE': [auth_func]
                       },
                       postprocessors={
                           'POST': [post_create_review]
                       },
                       exclude_columns=models.User.exclude_fields(),
                       validation_exceptions=[DbException])

api_manager.create_api(models.ReviewLike,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['POST', 'PATCH'],
                       preprocessors={
                           'POST': [auth_func, pre_review_like_post],
                           'PATCH_SINGLE': [auth_func]
                       },
                       exclude_columns=models.User.exclude_fields(),
                       validation_exceptions=[DbException])

api_manager.create_api(models.Order,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['GET'],
                       preprocessors={
                           'GET_SINGLE': [auth_func, req_shop_owner],
                           'GET_MANY': [auth_func, req_shop_owner]
                       }, )

api_manager.create_api(models.Notification,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['GET'],
                       preprocessors={
                           'GET_SINGLE': [auth_func],
                           'GET_MANY': [auth_func],
                           'PATCH_SINGLE': [auth_func, read_notification]
                       }, )

api_manager.create_api(models.Shop,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['PATCH'],
                       preprocessors={
                           'PATCH_SINGLE': [req_shop_owner, is_shop_owned_by_user]
                       },
                       validation_exceptions=[DbException])


@api.route('/auth', methods=['POST'])
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
    user = models.User.get_by_email(email)
    verify_password(password, user.password)
    login_user(user)
    return jsonify({}), 200


from webapp.api.webhooks import shopify


# from flask import jsonify, request
# from flask.ext.security import login_user, login_required, current_user
# from webapp import db, review_photos
# from webapp.common import get_post_payload, param_required, build_created_response, reviewer_required, verify_webhook, \
#     shop_owner_required, catch_exceptions
# from webapp.models import User, Product, ShopProduct, Review, Order, Shop, Notification, ShopProductReview
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
#     shop_review = ShopProductReview.get_by_review_id(review_id)
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
