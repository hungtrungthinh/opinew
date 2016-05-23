from flask import Blueprint

vgiphy = Blueprint('vgiphy', __name__)
from . import views