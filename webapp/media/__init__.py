from flask import Blueprint

media = Blueprint('media', __name__)
from . import views