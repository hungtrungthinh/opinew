from flask import Blueprint

vstripe = Blueprint('vstripe', __name__)
from . import views