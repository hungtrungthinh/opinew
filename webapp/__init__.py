from flask import Flask
from flask_httpauth import HTTPBasicAuth
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.uploads import IMAGES, UploadSet, configure_uploads

from config import Config


app = Flask(__name__)
auth = HTTPBasicAuth()
app.config.from_object(Config)

db = SQLAlchemy(app)

user_photos = UploadSet('userphotos', IMAGES)
review_photos = UploadSet('reviewphotos', IMAGES)
configure_uploads(app, (user_photos, review_photos, ))

import models
import views

db.create_all()
users = models.User.query.all()
if not users:
    user = models.User(name="Daniel Tsvetkov", email='danieltcv@gmail.com', password='password')
    db.session.add(user)

product = models.Product(label='Nexus 5')
db.session.add(product)

shops = models.Shop.query.all()
if not shops:
    shop = models.Shop()
    shop.products.append(product)
    db.session.add(shop)


db.session.commit()
