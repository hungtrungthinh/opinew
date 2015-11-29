import json
import base64
import random
import string
import hmac
import hashlib
import datetime
from functools import wraps
from flask import jsonify, abort, request, url_for, current_app
from flask.ext.login import current_user
from werkzeug.exceptions import HTTPException
from webapp.exceptions import ParamException, ApiException, DbException
from config import Constants, Config
from sqlalchemy.exc import InvalidRequestError


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


def random_pwd(length):
    return ''.join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(length))


def generate_temp_password():
    from webapp.models import User

    users = User.query.all()
    while True:
        temp_password = random_pwd(Constants.TEMP_PWD_LEN)
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
    response.headers['Location'] = current_app.config.get('OPINEW_API_SERVER') + url_for(url_for_name, **kwargs)
    response.autocorrect_location_header = False
    return response


def catch_exceptions(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except (ApiException, ParamException, DbException, InvalidRequestError) as e:
            status_code = e.status_code if hasattr(e, 'status_code') else 400
            return jsonify({"error": e.message}), status_code

    return wrapper


def role_required(f):
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
        calculated_hmac = base64.b64encode(
            hmac.new(Config.SHOPIFY_APP_SECRET, msg=request.data, digestmod=hashlib.sha256).digest())
        if not calculated_hmac == request_hmac:
            raise ParamException("Invalid signature.", 403)
        return f(*args, **kwargs)

    return wrapper


def create_jinja_filters(app):
    @app.template_filter('timesince')
    def timesince(dt, default="just now"):
        """
        Returns string representing "time since" e.g.
        3 days ago, 5 hours ago etc.
        """
        if not dt:
            return ''

        now = datetime.datetime.utcnow()
        diff = now - dt

        periods = (
            (diff.days / 365, "year", "years"),
            (diff.days / 30, "month", "months"),
            (diff.days / 7, "week", "weeks"),
            (diff.days, "day", "days"),
            (diff.seconds / 3600, "hour", "hours"),
            (diff.seconds / 60, "minute", "minutes"),
            (diff.seconds, "second", "seconds"),
        )

        for period, singular, plural in periods:

            if period:
                return "%d %s ago" % (period, singular if period == 1 else plural)

        return default

    @app.template_filter('timeto')
    def timeto(dt, default="just now"):
        """
        Returns string representing "time since" e.g.
        3 days ago, 5 hours ago etc.
        """
        if not dt:
            return ''

        now = datetime.datetime.utcnow()
        diff = dt - now

        periods = (
            (diff.days / 365, "year", "years"),
            (diff.days / 30, "month", "months"),
            (diff.days / 7, "week", "weeks"),
            (diff.days, "day", "days"),
            (diff.seconds / 3600, "hour", "hours"),
            (diff.seconds / 60, "minute", "minutes"),
            (diff.seconds, "second", "seconds"),
        )

        for period, singular, plural in periods:

            if period:
                return "%d %s" % (period, singular if period == 1 else plural)

        return default


def inject_ua(ua_str, kwargs):
    if 'headers' in kwargs:
        kwargs['headers']['user-agent'] = ua_str
    else:
        kwargs['headers'] = {'user-agent': ua_str}
    return kwargs
