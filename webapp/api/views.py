import datetime
import requests
from flask import jsonify, current_app, request, session
from flask_wtf.csrf import generate_csrf
from flask.ext.security import login_user, current_user, login_required
from flask.ext.security.utils import verify_password
from flask.ext.restless import ProcessingException
from webapp import api_manager, models, db, csrf
from webapp.api import api
from webapp.common import get_post_payload, param_required, catch_exceptions, random_pwd
from webapp.exceptions import DbException, ExceptionMessages, UserExistsException
from config import Constants
from urlparse import urlsplit


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
    data['action'] = '1'


def pre_review_like_patch(data, *args, **kwargs):
    review_id = data.get('review_id')
    if not review_id:
        raise ProcessingException(description='Review id requried!', code=401)
    review = models.Review.query.filter_by(id=review_id).first()
    if not review:
        raise ProcessingException(description='Review doesnt exist', code=401)
    review_like = models.ReviewLike.query.filter_by(review_id=review_id, user_id=current_user.id).first()
    if not review_like:
        raise ProcessingException(description='Review hasn\'t been liked before', code=401)
    data['user_id'] = current_user.id
    if data['action'] not in ['0', '1']:
        raise ProcessingException(description='Incorrect value for action.', code=401)


def pre_review_report_post(data, *args, **kwargs):
    review_id = data.get('review_id')
    if not review_id:
        raise ProcessingException(description='Review id requried!', code=401)
    review = models.Review.query.filter_by(id=review_id).first()
    if not review:
        raise ProcessingException(description='Review doesnt exist', code=401)
    review_report = models.ReviewReport.query.filter_by(review_id=review_id, user_id=current_user.id).first()
    if review_report:
        raise ProcessingException(description='You have already reported this review', code=401)
    data['user_id'] = current_user.id
    data['action'] = '1'


def pre_review_report_patch(data, *args, **kwargs):
    review_id = data.get('review_id')
    if not review_id:
        raise ProcessingException(description='Review id requried!', code=401)
    review = models.Review.query.filter_by(id=review_id).first()
    if not review:
        raise ProcessingException(description='Review doesnt exist', code=401)
    review_report = models.ReviewReport.query.filter_by(review_id=review_id, user_id=current_user.id).first()
    if not review_report:
        raise ProcessingException(description='This review hasn\'t been reported before', code=401)
    if data['action'] not in ['0', '1']:
        raise ProcessingException(description='Incorrect value for action.', code=401)


def pre_review_feature_post(data, *args, **kwargs):
    review_id = data.get('review_id')
    if not review_id:
        raise ProcessingException(description='Review id requried!', code=401)
    review = models.Review.query.filter_by(id=review_id).first()
    if not review:
        raise ProcessingException(description='Review doesnt exist', code=401)
    review_feature = models.ReviewFeature.query.filter_by(review_id=review_id).first()
    if review_feature:
        raise ProcessingException(description='You have already featured this review', code=401)
    data['action'] = '1'


def pre_review_feature_patch(data, *args, **kwargs):
    review_id = data.get('review_id')
    if not review_id:
        raise ProcessingException(description='Review id requried!', code=401)
    review = models.Review.query.filter_by(id=review_id).first()
    if not review:
        raise ProcessingException(description='Review doesnt exist', code=401)
    review_feature = models.ReviewFeature.query.filter_by(review_id=review_id).first()
    if not review_feature:
        raise ProcessingException(description='This review hasn\'t been featured before.', code=401)
    if data['action'] not in ['0', '1']:
        raise ProcessingException(description='Incorrect value for action.', code=401)


def pre_create_order(data, *args, **kwargs):
    shop_id = data.get('shop_id')
    if not shop_id:
        raise ProcessingException(description='Shop id required', code=401)
    shop = models.Shop.query.filter_by(id=shop_id).first()
    if not shop.owner == current_user:
        raise ProcessingException(description='Not your shop', code=401)
    data['purchase_timestamp'] = unicode(datetime.datetime.utcnow())


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


def pre_create_shop(data, *args, **kwargs):
    data['owner_id'] = current_user.id


def is_notification_by_user(instance_id, *args, **kwargs):
    notification = models.Notification.query.filter_by(id=int(instance_id)).first()
    if not notification or not notification.user == current_user:
        raise ProcessingException(description='Not your notification', code=401)


def get_many_notifications_preprocessor(search_params, **kw):
    """Accepts a single argument, `search_params`, which is a dictionary
    containing the search parameters for the request.
    """
    search_params["filters"] = [{"name":"user_id", "op":"==", "val":current_user.id}]


def pre_notification_patch(instance_id, data, *args, **kwargs):
    if not instance_id:
        raise ProcessingException(description='Notification id requried!', code=401)
    notification = models.Notification.query.filter_by(id=instance_id).first()
    if not notification:
        raise ProcessingException(description='Review doesnt exist', code=401)
    data['is_read'] = True


def is_shop_owned_by_user(instance_id, *args, **kwargs):
    shop = models.Shop.query.filter_by(id=instance_id).first()
    if not shop or not shop.owner == current_user:
        raise ProcessingException(description='Not your shop', code=401)


def del_user_id(data, *args, **kwargs):
    if 'user_id' in data:
        del data['user_id']


def check_recaptcha(data, *args, **kwargs):
    if current_user.is_authenticated():
        if 'g-recaptcha-response' in data:
            del data['g-recaptcha-response']
        return
    # TODO: return if the user comes from a verified source
    if 'review_request_id' in data and 'review_request_token' in data:
        review_request = models.ReviewRequest.query.filter_by(id=data.get('review_request_id')).first()
        if review_request and review_request.token == data.get('review_request_token'):
            if 'g-recaptcha-response' in data:
                del data['g-recaptcha-response']
            return
    recaptcha = data.get('g-recaptcha-response')
    if not recaptcha:
        raise ProcessingException(description=ExceptionMessages.MISSING_PARAM % 'g-recaptcha-response', code=401)
    r = requests.post(current_app.config.get("RECAPTCHA_URL"),
                      data={
                          'secret': current_app.config.get("RECAPTCHA_SECRET"),
                          'response': recaptcha,
                          'remoteip': request.remote_addr
                      })
    if not (r and r.status_code == 200 and r.json()):
        raise ProcessingException(description=ExceptionMessages.CAPTCHA_FAIL, code=401)
    if not r.json().get('success'):
        raise ProcessingException(description=ExceptionMessages.CAPTCHA_FAIL, code=401)

    del data['g-recaptcha-response']


def check_if_user_exists(data, *args, **kwargs):
    if current_user.is_authenticated():
        data["user_id"] = current_user.id
        return
    user_name = data.get('user_name')
    user_email = data.get('user_email')
    user_legacy_email = None
    if 'user_legacy_email' in data:
        user_legacy_email = data.get('user_legacy_email')
        del data['user_legacy_email']

    if not user_name:
        raise ProcessingException(description=ExceptionMessages.MISSING_PARAM % 'user_name', code=401)

    if not user_email:
        raise ProcessingException(description=ExceptionMessages.MISSING_PARAM % 'user_email', code=401)

    user, is_new = models.User.get_or_create_by_email(email=user_email, role_name=Constants.REVIEWER_ROLE,
                                                      user_legacy_email=user_legacy_email, name=user_name)
    if not is_new:
        #TODO maybe display a passwd field if user is not new?
        raise ProcessingException(description=ExceptionMessages.USER_EXISTS % user_email, code=401)

    db.session.add(user)
    db.session.commit()
    login_user(user)

    if 'user_name' in data:
        del data['user_name']
    del data['user_email']
    data['user_id'] = user.id


def is_verified_review(data, *args, **kwargs):
    # Is it verified review?
    review_request_id = data.get('review_request_id')
    if review_request_id and models.Review.verify_review_request(data):
        data['verified_review'] = True
        del data['review_request_id']
        del data['review_request_token']


def add_source(data, *args, **kwargs):
    # Coming from opinew
    source_opinew = models.Source.query.filter_by(name='opinew').first()
    if source_opinew:
        data['source_id'] = source_opinew.id


def login_user_if_possible(data, *args, **kwargs):
    if "user_email" in data and "user_password" in data:
        email = data["user_email"]
        password = data["user_password"]
        user = models.User.query.filter_by(email=email).first()
        if not user:
            raise ProcessingException(description='unauthorized', code=401)
        if not verify_password(password, user.password):
            raise ProcessingException(description='unauthorized', code=401)
        login_user(user)
        del data["user_password"]
        if 'user_name' in data:
            del data['user_name']
        del data['user_email']
        data["user_id"] = user.id


def pre_post_question(data, *args, **kwargs):
    if current_user and current_user.is_authenticated():
        data['user_id'] = current_user.id
    else:
        temp_user_id = data.get('temp_user_id') or session.get('temp_user_id')
        if not temp_user_id:
            user = models.User()
            db.session.add(user)
            db.session.commit()
            temp_user_id = user.id
        session['temp_user_id'] = temp_user_id
        data['user_id'] = temp_user_id


def pre_post_answer(data, *args, **kwargs):
    question_id = data.get('to_question_id')
    if not question_id:
        raise ProcessingException(description='Question id required', code=401)
    question = models.Question.query.filter_by(id=question_id).first()
    if not question:
        raise ProcessingException(description='Question doesnt exist', code=401)
    shop_id = question.about_product.shop.id
    shop = models.Shop.query.filter_by(id=shop_id).first()
    if not shop.owner == current_user:
        raise ProcessingException(description='Not your shop', code=401)
    data['user_id'] = current_user.id


def shop_domain_parse(data, *args, **kwargs):
    domain = data['domain']
    splitted = urlsplit(domain)
    if splitted.scheme == "":
        domain = "http://"+domain
    elif splitted.scheme in ["http", "https"]:
        domain = splitted.scheme + "://" + splitted.netloc
    else:
        raise ProcessingException(description="Sorry, we couldn't process your shop domain name. "
                                              "Are you sure it looks like one of these? "
                                              "https://www.shop.com, http://www.shop.com, www.shop.com", code=401)
    data["domain"] = domain



# To query the reviews:
# http://flask-restless.readthedocs.org/en/latest/searchformat.html
# e.g. http://localhost:5000/api/v1/review?q={"order_by": [{"field": "created_ts", "direction":"desc"}], "offset":10}
api_manager.create_api(models.Review,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['GET', 'POST'],
                       preprocessors={
                           'POST': [del_csrf, check_recaptcha, login_user_if_possible, check_if_user_exists, is_verified_review, add_source],
                           'PATCH_SINGLE': [del_csrf, auth_func]
                       },
                       exclude_columns=models.Review.exclude_fields(),
                       validation_exceptions=[DbException, UserExistsException])

api_manager.create_api(models.ReviewLike,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['POST', 'PATCH'],
                       preprocessors={
                           'POST': [del_csrf, auth_func, pre_review_like_post],
                           'PATCH_SINGLE': [del_csrf, auth_func, pre_review_like_patch]
                       },
                       exclude_columns=models.User.exclude_fields(),
                       validation_exceptions=[DbException])

api_manager.create_api(models.ReviewReport,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['POST', 'PATCH'],
                       preprocessors={
                           'POST': [del_csrf, auth_func, pre_review_report_post],
                           'PATCH_SINGLE': [del_csrf, auth_func, pre_review_report_patch]
                       },
                       exclude_columns=models.User.exclude_fields(),
                       validation_exceptions=[DbException])

api_manager.create_api(models.ReviewFeature,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['POST', 'PATCH'],
                       preprocessors={
                           'POST': [del_csrf, auth_func, req_shop_owner, pre_review_feature_post],
                           'PATCH_SINGLE': [del_csrf, auth_func, req_shop_owner, pre_review_feature_patch]
                       },
                       exclude_columns=models.User.exclude_fields(),
                       validation_exceptions=[DbException])

api_manager.create_api(models.Order,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['POST'],
                       preprocessors={
                           'POST': [del_csrf, req_shop_owner, pre_create_order],
                       }, )

api_manager.create_api(models.User,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['GET'],
                       include_columns=models.User.include_own_fields(),
                       validation_exceptions=[DbException])

api_manager.create_api(models.Notification,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['GET', 'PATCH'],
                       preprocessors={
                           'GET_SINGLE': [auth_func, is_notification_by_user],
                           'GET_MANY': [auth_func, get_many_notifications_preprocessor],
                           'PATCH_SINGLE': [del_csrf, auth_func, is_notification_by_user, pre_notification_patch]
                       }, )

api_manager.create_api(models.Shop,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['POST', 'PATCH'],
                       preprocessors={
                           'POST': [del_csrf, req_shop_owner, pre_create_shop],
                           'PATCH_SINGLE': [del_csrf, req_shop_owner, is_shop_owned_by_user]
                       },
                       validation_exceptions=[DbException])

api_manager.create_api(models.Product,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['GET', 'POST', 'PATCH'],
                       preprocessors={
                           'POST': [del_csrf, req_shop_owner, pre_create_product],
                           'PATCH_SINGLE': [del_csrf, req_shop_owner]
                       }, )

api_manager.create_api(models.Question,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['POST'],
                       preprocessors={
                           'POST': [del_csrf, pre_post_question],
                       },
                       validation_exceptions=[DbException])

api_manager.create_api(models.Answer,
                       url_prefix=Constants.API_V1_URL_PREFIX,
                       methods=['POST'],
                       preprocessors={
                           'POST': [del_csrf, req_shop_owner, pre_post_answer],
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

@api.route('/check-user-exists', methods=['GET'])
@csrf.exempt
@catch_exceptions
def check_if_user_exists():
    user_email = request.args.get('user_email')
    user = models.User.get_by_email_no_exception(email=user_email)
    if user:
        return jsonify({"message": "exists"})
    return jsonify({"message":"newuser"})

from webapp.api.webhooks import shopify
