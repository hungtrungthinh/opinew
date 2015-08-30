from flask import Flask
from flask_httpauth import HTTPBasicAuth
from flask.ext.sqlalchemy import SQLAlchemy


app = Flask(__name__)
auth = HTTPBasicAuth()
app.config.update(
    DEBUG=True,
    SECRET_KEY='fheiy3rihiewui4439845ty89o',
    SQLALCHEMY_DATABASE_URI='sqlite:////tmp/ecommerce_api.db',
)

db = SQLAlchemy(app)

import models
import views

db.create_all()
users = models.User.query.all()
if not users:
    user = models.User(email='danieltcv@gmail.com', password='password')
    db.session.add(user)

products = models.Product.query.all()
if not products:
    product = models.Product(label='Nexus 5')
    db.session.add(product)

db.session.commit()
