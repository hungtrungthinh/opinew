from flask import Blueprint

vshopify = Blueprint('vshopify', __name__)
from . import views