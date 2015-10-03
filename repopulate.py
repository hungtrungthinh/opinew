#!venv/bin/python
import os
import sys
import csv
from flask import url_for
from webapp import models, db, create_app
from config import Constants, basedir

# populate tables
arguments = sys.argv
if not len(sys.argv) == 2 or arguments[1] not in ['db_dev', 'db_prod']:
    print "USAGE: ./repopulate.py db_dev|db_prod"
    exit(1)
option = arguments[1]
app = create_app(option)

db.init_app(app)

try:
    os.remove('/tmp/ecommerce_api.db')
    os.remove('/home/opinew_server/db/ecommerce_api.db')
except OSError:
    pass

###############################
# INIT DB
###############################
app.app_context().push()
db.create_all()

###############################
# CREATE USERS
###############################
with open(os.path.join(basedir, 'install', 'init_db', 'User.csv'), 'r') as csvfile:
    userreader = csv.reader(csvfile)
    csvfile.readline()  # skip first line
    for row in userreader:
        user = models.User(email=row[1], password=row[2], name=row[3], profile_picture_url=row[4],
                           role=Constants.REVIEWER_ROLE)
        db.session.add(user)

###############################
# CREATE PLATFORMS
###############################
shopify_platform = models.Platform(name='shopify')
custom_platform = models.Platform(name='custom')
db.session.add(shopify_platform)

###############################
# CREATE SHOPS
###############################
# Create opinew shop
SHOP_URL = 'http://shop.opinew.com'
jack_owner = models.User(name="Jack Shepard", role=Constants.SHOP_OWNER_ROLE, email='juliet@opinew.com')
opinew_shop = models.Shop(label='Opinew shop', domain=SHOP_URL, platform=custom_platform)
opinew_shop.owner = jack_owner
db.session.add(opinew_shop)


###############################
# CREATE PRODUCTS
###############################
with open(os.path.join(basedir, 'install', 'init_db', 'Product.csv'), 'r') as csvfile:
    productreader = csv.reader(csvfile)
    csvfile.readline()  # skip first line
    for row in productreader:
        product = models.Product(label=row[1])
        shop_product = models.ShopProduct(shop=opinew_shop, product=product, url="%s/product/%s" % (SHOP_URL, row[0]),
                                          platform_product_id=row[0])
        db.session.add(shop_product)

###############################
# CREATE REVIEWS
###############################
with open(os.path.join(basedir, 'install', 'init_db', 'Review.csv'), 'r') as csvfile:
    reviewreader = csv.reader(csvfile)
    csvfile.readline()  # skip first line
    for row in reviewreader:
        user = models.User.query.filter_by(id=row[4]).first()
        product = models.Product.query.filter_by(id=row[5]).first()
        shop_product = models.ShopProduct.query.filter_by(shop=opinew_shop, product=product).first()
        review = models.Review(user=user, product=product, body=row[1], photo_url=row[3], shop_product=shop_product)
        shop_review = models.ShopReview(shop=opinew_shop, review=review)
        shop_review.approved_by_shop = True
        shop_review.approval_pending = False
        db.session.add(shop_review)

# Flush to db
db.session.commit()
