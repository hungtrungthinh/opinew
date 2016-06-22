import json
import base64
import random
import string
import hmac
import hashlib
import datetime
import traceback
from functools import wraps
from flask import jsonify, abort, request, url_for, current_app, render_template
from flask.ext.login import current_user
from werkzeug.exceptions import HTTPException
from webapp.exceptions import ParamException, ApiException, DbException
from config import Constants, Config
from sqlalchemy.exc import InvalidRequestError

def verify_initialization():
    from webapp import models
    # Check that the free plan exists in the database
    basic_plan = models.Plan.query.filter_by(name=Constants.PLAN_NAME_BASIC).first()
    simple_plan = models.Plan.query.filter_by(name=Constants.PLAN_NAME_SIMPLE).first()
    assert basic_plan is not None
    assert simple_plan is not None


# Make json error handlers
def make_json_error(ex):
    from webapp.flaskopinewext import error_string
    # don't send email on 404
    if hasattr(ex, 'code') and ex.code == 404 and request.base_url not in ['https://opinew.com', 'https://opinew.com/']:
        response = jsonify(error=str(ex))
        response.status_code = 404
        return response
    current_app.logger.error(error_string(ex))
    status_code = ex.code if isinstance(ex, HTTPException) else 500
    # return pretty rendered templates messages to a client request
    if request.blueprint == 'client':
        if status_code == 500:
            return render_template('errors/500.html'), 500
    response = jsonify(error=str(ex))
    response.status_code = status_code
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

import httplib
import json
from functools import wraps
from werkzeug.routing import BuildError
from werkzeug.datastructures import ImmutableMultiDict
from flask import request, current_app, url_for, jsonify, flash, redirect
from messages import SuccessMessages
from webapp.exceptions import RequirementException, ExceptionMessages
from config import Constants

def verify_requirements(*redirect_url_for):
    """
    Wraps a response object by verifying that all required conditions pass
    :param f:
    :return:
    """
    def outer_wrapper(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Create a response context - is it asyncrounous call (e.g. from ajax)
            payload = request.args if request.method in ['GET'] else request.form or json.loads(request.data or '{}')
            is_async = payload.get('async')

            # get as many default redirects as possible
            default_redirects = []
            for redirect_url in redirect_url_for:
                try:
                    default_redirects.append(url_for(redirect_url))
                except BuildError:
                    # well, this url_for was invalid, don't break everything, move on
                    pass

            # decide which exceptions to catch
            if current_app.debug:
                exception_list = (RequirementException, )
            else:
                exception_list = (Exception, )
            try:
                return f(*args, **kwargs)
            except exception_list as e:
                error_message = e.message or ExceptionMessages.UNKNOWN_ERROR
                error_code = e.error_code if hasattr(e, 'error_code') else httplib.BAD_REQUEST
                error_category = e.error_category if hasattr(e, 'error_category') else Constants.ALERT_ERROR_LABEL

                # If it an async request - then return jsonified response
                if is_async:
                    return jsonify({"error": error_message}), error_code
                flash(error_message, category=error_category)

                # try to avoid 1 level deep infinite loop redirect
                referer_redirect = request.referrer if not request.referrer == request.path else None
                ctx_redirect = None
                for default_redirect in default_redirects:
                    ctx_redirect = default_redirect if not default_redirect == request.path else None
                    if ctx_redirect:
                        break
                return redirect(referer_redirect or
                                ctx_redirect or
                                url_for('client.index'))
        return wrapper
    return outer_wrapper


def always_async(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        request_args = dict(request.args)
        request_args['async'] = 1
        request.args = ImmutableMultiDict(request_args)
        return f(*args, **kwargs)
    return wrapper


def verify_required_condition(condition, error_msg, error_code=httplib.BAD_REQUEST, error_category=Constants.ALERT_ERROR_LABEL):
    """
    Makes sure that the required condition is truthy. Otherwise raises a response error which is either
    jsonified response (if the resource has been required async) or flashing.
    :param condition: the condition
    :param error_msg: the error message to display
    :param error_code: the error code to return
    :return:
    """
    if not condition:
        raise RequirementException(message=error_msg, error_code=error_code, error_category=error_category)


def get_required_parameter(payload, param_name):
    """
    Verifies and returns a parameter from a payload
    :param payload: the payload to check
    :param param_name: the parameter name
    :return:
    """
    obj = payload.get(param_name)
    verify_required_condition(condition=obj is not None,
                              error_msg=ExceptionMessages.MISSING_PARAM.format(param=param_name),
                              error_code=httplib.BAD_REQUEST)
    return obj


def get_required_model_instance_by_id(model, instance_id):
    """
    Verifies and returns a model instance that is identified by id
    :param model: the Model to check
    :param instance_id: the instance id
    :return: a model instance by id
    """
    obj = model.query.filter_by(id=instance_id).first()
    verify_required_condition(condition=obj is not None,
                           error_msg=ExceptionMessages.INSTANCE_NOT_EXISTS.format(instance=model.__name__,
                                                                                  id=instance_id),
                           error_code=httplib.BAD_REQUEST)
    return obj


def generate_success_response_from_obj(obj, obj_name):
    payload = request.args if request.method in ['GET'] else request.form or json.loads(request.data)
    is_async = payload.get('async')
    if is_async:
        return jsonify(obj), httplib.CREATED
    flash(SuccessMessages.SUCCESS_CREATING_OBJECT.format(object_name=obj_name))
    return redirect(request.referrer)


def generate_success_response_from_model(model, obj_name):
    return generate_success_response_from_obj(model.serialize(), obj_name)