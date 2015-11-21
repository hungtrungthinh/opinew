import datetime
from flask import jsonify
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


def is_verified_review(data, *args, **kwargs):
    # Is it verified review?
    review_request_id = data.get('review_request_id')
    if review_request_id and models.Review.verify_review_request(data):
        data['verified_review'] = True
        del data['review_request_id']
        del data['review_request_token']
    return data


api_manager.create_api(models.Product,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['GET', 'POST', 'PATCH'],
                       preprocessors={
                           'POST': [del_csrf, req_shop_owner, pre_create_product],
                           'PATCH_SINGLE': [del_csrf, req_shop_owner]
                       }, )


# To query the reviews:
# http://flask-restless.readthedocs.org/en/latest/searchformat.html
# TODO: TEST THIS SHIT
# e.g. http://localhost:5000/api/v1/review?q={"order_by": [{"field": "created_ts", "direction":"desc"}], "offset":10}
api_manager.create_api(models.Review,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['GET', 'POST'],
                       preprocessors={
                           'POST': [del_csrf, auth_func, is_verified_review],
                           'PATCH_SINGLE': [del_csrf, auth_func]
                       },
                       exclude_columns=models.Review.exclude_fields(),
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
                           'GET_MANY': [auth_func, req_shop_owner],
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
