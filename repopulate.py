#!venv/bin/python
import os
import sys
import csv
from webapp import models, db, create_app
from config import Constants, basedir
from flask.ext.security.utils import encrypt_password
import sensitive

class Repopulate(object):
    def __init__(self):
        self.ADMIN_PASSWORD = sensitive.ADMIN_PASSWORD
        self.REVIEWER_PASSWORD = 'password'
        self.OWNER_PASSWORD = 'owner_password'
        self.SHOP_URL = 'http://shop.opinew.com'

        self.admin_role, self.shop_owner_role, self.reviewer_role, self.shopify_platform, self.custom_platform, self.null_shop, self.shop_owner, self.opinew_shop = None, None,None, None,None,None, None, None

    def populate_dev(self):
        ###############################
        # CREATE USERS
        ###############################
        with open(os.path.join(basedir, 'install', 'init_db', 'User.csv'), 'r') as csvfile:
            userreader = csv.reader(csvfile)
            csvfile.readline()  # skip first line
            for row in userreader:
                user = models.User(email=row[1], password=encrypt_password(row[2]), name=row[3], profile_picture_url=row[4])
                role = models.Role.query.filter_by(name=row[5]).first()
                user.roles.append(role)
                db.session.add(user)

        ###############################
        # CREATE PRODUCTS
        ###############################
        with open(os.path.join(basedir, 'install', 'init_db', 'Product.csv'), 'r') as csvfile:
            productreader = csv.reader(csvfile)
            csvfile.readline()  # skip first line
            for row in productreader:
                product = models.Product(name=row[1])
                shop_product = models.ShopProduct(shop=self.opinew_shop, product=product,
                                                  url="%s/product/%s" % (self.SHOP_URL, row[0]),
                                                  platform_product_id=row[0])
                db.session.add(shop_product)

        ###############################
        # CREATE ORDERS
        ###############################
        order_1 = models.Order(user=models.User.query.filter_by(id=3).first(),
                               shop=self.opinew_shop,
                               )
        order_1.products.append(models.Product.query.filter_by(id=1).first())
        order_1.products.append(models.Product.query.filter_by(id=2).first())
        db.session.add(order_1)

        ###############################
        # CREATE REVIEWS
        ###############################
        with open(os.path.join(basedir, 'install', 'init_db', 'Review.csv'), 'r') as csvfile:
            reviewreader = csv.reader(csvfile)
            csvfile.readline()  # skip first line
            for row in reviewreader:
                user = models.User.query.filter_by(id=row[4]).first()
                product = models.Product.query.filter_by(id=row[5]).first()
                shop_product = models.ShopProduct.query.filter_by(shop=self.opinew_shop, product=product).first()
                review = models.Review.create_from_repopulate(user=user, shop_product_id=shop_product.id,
                                       body=unicode(row[1]), photo_url=unicode(row[3]), star_rating=row[2])
                shop_review = models.ShopProductReview(shop_product=shop_product, review=review)
                shop_review.approved_by_shop = True
                shop_review.approval_pending = False
                db.session.add(shop_review)

    def populate_test(self):
        reviewer = models.User(name="Reviewer", email='reviewer@opinew.com', password=self.REVIEWER_PASSWORD)
        reviewer.roles.append(self.reviewer_role)
        db.session.add(reviewer)

        admin = models.User(name="Admin", email='danieltcv@opinew.com', password=self.ADMIN_PASSWORD)
        admin.roles.append(self.admin_role)
        db.session.add(admin)

        product = models.Product(name='Ear rings')
        shop_product = models.ShopProduct(shop=self.opinew_shop,
                                          product=product,
                                          url="%s/product/%s" % (self.SHOP_URL, 1),
                                          platform_product_id=1)
        db.session.add(shop_product)

        review = models.Review.create_from_repopulate(user=reviewer, shop_product_id=1,
                                                      body=unicode("Nice"), photo_url=unicode("/test.png"),
                                                      star_rating=5)
        shop_review = models.ShopProductReview(shop_product=shop_product, review=review)
        shop_review.approved_by_shop = True
        shop_review.approval_pending = False
        db.session.add(shop_review)

    def populate_db(self, option):
        ###############################
        # CREATE ROLES
        ###############################
        self.admin_role = models.Role(name=Constants.ADMIN_ROLE, description='Admins only')
        self.shop_owner_role = models.Role(name=Constants.SHOP_OWNER_ROLE, description='Shop owners only')
        self.reviewer_role = models.Role(name=Constants.REVIEWER_ROLE, description='Reviewers only')
        db.session.add(self.admin_role)
        db.session.add(self.shop_owner_role)
        db.session.add(self.reviewer_role)

        ###############################
        # CREATE PLATFORMS
        ###############################
        self.shopify_platform = models.Platform(name='shopify')
        self.custom_platform = models.Platform(name='custom')
        db.session.add(self.shopify_platform)
        db.session.add(self.custom_platform)

        ###############################
        # CREATE SHOPS
        ###############################
        # Create null shop
        self.null_shop = models.Shop()
        db.session.add(self.null_shop)

        # Create opinew shop
        SHOP_URL = 'http://shop.opinew.com'
        self.shop_owner = models.User(name="Shop Owner", email='owner@opinew.com', password=self.OWNER_PASSWORD)
        self.shop_owner.roles.append(self.shop_owner_role)
        db.session.add(self.shop_owner)

        self.opinew_shop = models.Shop(name='Opinew shop', domain=SHOP_URL, platform=self.custom_platform)
        self.opinew_shop.owner = self.shop_owner
        db.session.add(self.opinew_shop)

        if option == 'test':
            self.populate_test()
        elif option == 'dev':
            self.populate_dev()
        # Flush to db
        db.session.commit()


if __name__ == '__main__':
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
    # POPULATE DB
    ###############################
    Repopulate().populate_db('dev')
