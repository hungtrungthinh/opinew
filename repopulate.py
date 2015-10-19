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
        self.SHOP_URL = 'http://opinew_shop.local:5001'

        self.admin_role, self.shop_owner_role, self.reviewer_role, self.shopify_platform, self.custom_platform, self.null_shop, self.shop_owner, self.opinew_shop = None, None, None, None, None, None, None, None

    def populate_dev(self):
        ###############################
        # CREATE SUBSRTIPTION PLANS
        ###############################
        with open(os.path.join(basedir, 'install', 'init_db', 'SubscriptionPlan.csv'), 'r') as csvfile:
            spreader = csv.reader(csvfile)
            csvfile.readline()  # skip first line
            for row in spreader:
                plan = models.SubscriptionPlan(name=row[1],
                                               description=row[2],
                                               price=row[3],
                                               payment_frequency=row[4],
                                               active=row[5])
                db.session.add(plan)

        ###############################
        # CREATE USERS
        ###############################
        with open(os.path.join(basedir, 'install', 'init_db', 'User.csv'), 'r') as csvfile:
            userreader = csv.reader(csvfile)
            csvfile.readline()  # skip first line
            for row in userreader:
                user = models.User(email=row[1], password=encrypt_password(row[2]), name=row[3],
                                   profile_picture_url=row[4])
                role = models.Role.query.filter_by(name=row[5]).first()
                user.roles.append(role)
                db.session.add(user)

        # create shop owner USER
        self.shop_owner = models.User(name="Shop Owner", email='owner@opinew.com',
                                      password=encrypt_password(self.OWNER_PASSWORD))
        self.shop_owner.roles.append(self.shop_owner_role)
        db.session.add(self.shop_owner)

        # create shop owner CUSTOMER
        shop_owner_customer = models.Customer(user=self.shop_owner, current_subscription_plan_id=6)
        switch = models.CustomerSubscriptionPlanChange(customer=shop_owner_customer, new_subscription_plan_id=6)
        db.session.add(shop_owner_customer)
        db.session.add(switch)

        # Create opinew shop
        SHOP_URL = 'http://opinew_shop.local:5001/'
        self.opinew_shop = models.Shop(name='Opinew shop', domain=SHOP_URL, platform=self.custom_platform,
                                       description="Opinew is a contemporary fashion brand for the rebellious street fashion enthusiast. Each collection has an artistic story behind them and are designed in Scotland. We believe in unique clothing that you wont find on the high street!")
        self.opinew_shop.owner = self.shop_owner
        db.session.add(self.opinew_shop)

        ###############################
        # CREATE PRODUCTS
        ###############################
        with open(os.path.join(basedir, 'install', 'init_db', 'Product.csv'), 'r') as csvfile:
            productreader = csv.reader(csvfile)
            csvfile.readline()  # skip first line
            for row in productreader:
                product = models.Product(name=row[1],
                                         shop=self.opinew_shop,
                                         url="%s/product/%s" % (self.SHOP_URL, row[0]),
                                         platform_product_id=row[0])
                db.session.add(product)
        db.session.commit()

        ###############################
        # CREATE ORDERS
        ###############################
        order_1 = models.Order(user_id=3, shop_id=2, product_id=1)
        db.session.add(order_1)

        ###############################
        # CREATE REVIEWS
        ###############################
        with open(os.path.join(basedir, 'install', 'init_db', 'Review.csv'), 'r') as csvfile:
            reviewreader = csv.reader(csvfile)
            csvfile.readline()  # skip first line
            for row in reviewreader:
                review = models.Review.create_from_repopulate(user_id=row[4], product_id=row[5],
                                                              body=unicode(row[1]), photo_url=unicode(row[3]),
                                                              star_rating=row[2],
                                                              verified_review=row[6])
                review.product_review.approved_by_shop = True
                review.product_review.approval_pending = False

    def populate_test(self):
        admin = models.User(name="Admin", email='danieltcv@opinew.com', password=self.ADMIN_PASSWORD)
        admin.roles.append(self.admin_role)
        db.session.add(admin)

        reviewer = models.User(name="Reviewer", email='reviewer@opinew.com', password=self.REVIEWER_PASSWORD)
        reviewer.roles.append(self.reviewer_role)
        db.session.add(reviewer)

        # create shop owner USER
        self.shop_owner = models.User(name="Shop Owner", email='owner@opinew.com',
                                      password=encrypt_password(self.OWNER_PASSWORD))
        self.shop_owner.roles.append(self.shop_owner_role)
        db.session.add(self.shop_owner)

        # Create opinew shop
        SHOP_URL = 'http://opinew_shop.local:5001/'
        self.opinew_shop = models.Shop(name='Opinew shop', domain=SHOP_URL, platform=self.custom_platform)
        self.opinew_shop.owner = self.shop_owner
        db.session.add(self.opinew_shop)

        product = models.Product(name='Ear rings',
                                 url="%s/product/%s" % (self.SHOP_URL, 1),
                                 platform_product_id=1)
        db.session.add(product)

        review = models.Review.create_from_repopulate(user=reviewer, product_id=1,
                                                      body=unicode("Nice"), photo_url=unicode("/test.png"),
                                                      star_rating=5)
        shop_review = models.ProductReview(product=product, review=review)
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
        self.null_shop = models.Shop(name="NULL_SHOP")
        db.session.add(self.null_shop)

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
