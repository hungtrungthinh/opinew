from flask import Blueprint

vrecaptcha = Blueprint('vrecaptcha', __name__)
from . import views