import json
import base64
import random
import string
import hmac
import hashlib
from functools import wraps
from flask import jsonify, abort, request, url_for
from flask.ext.login import current_user
from werkzeug.exceptions import HTTPException
from webapp import auth
from webapp.exceptions import ParamException
from config import Constants, Config


@auth.get_password
def get_pw(username):
    from webapp.models import User

    user = User.query.filter_by(email=username).first()
    if user:
        return user.email
    return None


@auth.verify_password
def verify_pw(username, password):
    from webapp.models import User

    user = User.query.filter_by(email=username).first()
    if user:
        return user.validate_password(password)
    return False


def validate_user_role(role):
    if not current_user.role == role:
        abort(403)


# Make json error handlers
def make_json_error(ex):
    response = jsonify(error=str(ex))
    response.status_code = (ex.code
                            if isinstance(ex, HTTPException)
                            else 500)
    return response


def get_post_payload():
    if not request.form and not request.files:
        try:
            if request.data:
                return json.loads(request.data)
        except ValueError:
            raise ParamException("Invalid json in body of request.")
    else:
        return request.form
    return {}


def next_is_valid(next_url):
    if current_user.is_authenticated() and current_user.role:
        for access in current_user.role.access_whitelist:
            if next_url == access.url:
                return True
    return False


def generate_temp_password():
    from webapp.models import User

    users = User.query.all()
    while True:
        temp_password = ''.join(
            random.choice(string.ascii_uppercase + string.digits) for _ in range(Constants.TEMP_PWD_LEN))
        for user in users:
            if user.temp_password == temp_password:
                break
        return temp_password


def param_required(name=None, parameters=None):
    param = parameters.get(name, None)
    if param is None:
        raise ParamException(message='%s parameter is required' % name, status_code=400)
    return param


def build_created_response(url_for_name, **kwargs):
    response = jsonify()
    response.status_code = 201
    response.headers['Location'] = url_for(url_for_name, **kwargs)
    response.autocorrect_location_header = False
    return response


def open_with_auth(client, url, method, username, password, **kwargs):
    return client.open(url,
                       method=method,
                       headers={
                           'Authorization': 'Basic ' + base64.b64encode("%s:%s" % (username, password))
                       }, **kwargs)


def get_with_auth(client, url, username, password, **kwargs):
    return open_with_auth(client, url, 'get', username, password, **kwargs)


def post_with_auth(client, url, username, password, **kwargs):
    return open_with_auth(client, url, 'post', username, password, **kwargs)


def patch_with_auth(client, url, username, password, **kwargs):
    return open_with_auth(client, url, 'patch', username, password, **kwargs)

def shop_owner_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated() or not current_user.role == Constants.SHOP_OWNER_ROLE:
            abort(401)
        return f(*args, **kwargs)
    return wrapper

def reviewer_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated() or not current_user.role == Constants.REVIEWER_ROLE:
            abort(401)
        return f(*args, **kwargs)
    return wrapper

def verify_webhook(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        request_hmac = request.headers.get("X-Shopify-Hmac-SHA256")
        calulated_hmac = hmac.new(Config.SHOPIFY_APP_SECRET, msg=request.data, digestmod=hashlib.sha256).digest()
        if not calulated_hmac == request_hmac:
            raise ParamException("Invalid signature.", 403)
        return f(*args, **kwargs)
    return wrapper