from flask import Flask, jsonify
from werkzeug.exceptions import default_exceptions
from werkzeug.exceptions import HTTPException
from flask_httpauth import HTTPBasicAuth
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.uploads import IMAGES, UploadSet, configure_uploads

from config import Config

app = Flask(__name__)

# Make json error handlers
def make_json_error(ex):
    response = jsonify(error=str(ex))
    response.status_code = (ex.code
                            if isinstance(ex, HTTPException)
                            else 500)
    return response


for code in default_exceptions.iterkeys():
    app.error_handler_spec[None][code] = make_json_error

auth = HTTPBasicAuth()
app.config.from_object(Config)

db = SQLAlchemy(app)

user_photos = UploadSet('userphotos', IMAGES)
review_photos = UploadSet('reviewphotos', IMAGES)
configure_uploads(app, (user_photos, review_photos,))

import models
import views

# populate tables
db.create_all()
users = models.User.query.all()
if not users:
    user = models.User(name="Daniel Tsvetkov", email='danieltcv@gmail.com', password='password')
    db.session.add(user)

products = models.Product.query.all()
if not products:
    product = models.Product(label='Nexus 5')
    db.session.add(product)

    tags = models.Tag.query.all()
    if not tags:
        good_tag = models.Tag(label='Good', connotation=100)
        bad_tag = models.Tag(label='Bad', connotation=-100)

        product.tags.append(good_tag)
        product.tags.append(bad_tag)

    shops = models.Shop.query.all()
    if not shops:
        shop = models.Shop()
        shop.products.append(product)
        db.session.add(shop)

db.session.commit()
