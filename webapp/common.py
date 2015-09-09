import json
import random
import string
from flask import jsonify, abort, request
from flask.ext.login import current_user
from werkzeug.exceptions import HTTPException
from webapp import auth
from webapp.exceptions import ParamException
from config import Constants


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
            payload = json.loads(request.data)
        except ValueError:
            raise ParamException("Invalid json in body of request.")
    else:
        payload = request.form
    return payload


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
