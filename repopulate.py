#!venv/bin/python
import os
import sys
import csv
from webapp import models, db, create_app
from config import Constants, basedir
from flask.ext.security.utils import encrypt_password
from flask import current_app
import sensitive
from async import stripe_payment
from importers import magento


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
        with open(os.path.join(basedir, 'install', 'init_db', 'Plan.csv'), 'r') as csvfile:
            spreader = csv.reader(csvfile)
            csvfile.readline()  # skip first line
            for row in spreader:
                plan = models.Plan(name=row[1],
                                   description=row[2],
                                   amount=row[3],
                                   interval=row[4],
                                   trial_period_days=row[5],
                                   active=row[6])
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

        # BEAUTY KITCHEN USER
        self.beauty_kitchen_owner = models.User(name="Beauty Kitchen", email='info@fake_beautykitchen.co.uk',
                                      password=encrypt_password(self.OWNER_PASSWORD))
        self.beauty_kitchen_owner.roles.append(self.shop_owner_role)
        db.session.add(self.beauty_kitchen_owner)

        # NEEDED SO THAT THE PLANS ARE IN SYNC
        db.session.commit()
        pro_plan = models.Plan.query.filter_by(id=3).first()
        # TODO: Temporary disabled but works create shop owner CUSTOMER
        # 1. Get credit card token
        # stripe_api = stripe_payment.StripeAPI(current_app.config.get('STRIPE_API_KEY'))
        # stripe_token = stripe_api.create_token('4242424242424242', '123', 12, 2020).id
        # 2. Create Customer object
        # shop_owner_customer = models.Customer(stripe_token=stripe_token, user=self.shop_owner)
        # 3. Subscribe him to one of our plans (Pro)
        # subscription = models.Subscription(customer=shop_owner_customer, plan=pro_plan)
        # db.session.add(shop_owner_customer)
        # db.session.add(subscription)

        # Create opinew shop
        SHOP_URL = 'http://opinew_shop.local:5001/'
        self.opinew_shop = models.Shop(name='Opinew shop', domain=SHOP_URL, platform=self.custom_platform,
                                       description="Opinew is a contemporary fashion brand for the rebellious street fashion enthusiast. Each collection has an artistic story behind them and are designed in Scotland. We believe in unique clothing that you wont find on the high street!")
        self.opinew_shop.owner = self.shop_owner
        db.session.add(self.opinew_shop)

        # Create beauty kitchen shop
        BK_SHOP_URL = 'http://www.beautykitchen.co.uk/'
        self.beauty_kitchen_shop = models.Shop(name='Beauty Kitchen', domain=BK_SHOP_URL, platform=self.magento_platform,
                                       description="")
        self.beauty_kitchen_shop.owner = self.beauty_kitchen_owner
        db.session.add(self.beauty_kitchen_shop)

        ###############################
        # CREATE PRODUCTS
        ###############################
        with open(os.path.join(basedir, 'install', 'init_db', 'Product.csv'), 'r') as csvfile:
            productreader = csv.reader(csvfile)
            csvfile.readline()  # skip first line
            for row in productreader:
                product = models.Product(name=row[1],
                                         active=True,
                                         shop=self.opinew_shop,
                                         url="%s/product/%s" % (self.SHOP_URL, row[0]),
                                         platform_product_id=row[0])
                db.session.add(product)
        db.session.commit()

        magento_products = magento.products_import(os.path.join(basedir, 'tests', 'test_files', 'beauty_kitchen.csv'))
        BK_IMAGE_BASE = 'http://www.beautykitchen.co.uk/media/catalog/product/cache/1/image/363x/040ec09b1e35df139433887a97daa66f'
        for p in magento_products:
            if not p.get('name', None):
                continue
            product = models.Product(name=p.get('name'),
                                     active=True if p.get('status', 0) == u'1' else False,
                                     short_description=p.get('short_description'),
                                     product_type='Beauty Products',
                                     category=p.get('_category'),
                                     image_url="%s%s" % (BK_IMAGE_BASE, p.get('image')),
                                     shop=self.beauty_kitchen_shop,
                                     url="%s%s" % (BK_SHOP_URL, p.get('url_path')),
                                     platform_product_id=p.get('sku'))
            db.session.add(product)

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
        self.magento_platform = models.Platform(name='magento')
        self.woocommerce_platform = models.Platform(name='woocommerce')
        self.custom_platform = models.Platform(name='custom')
        db.session.add(self.shopify_platform)
        db.session.add(self.magento_platform)
        db.session.add(self.woocommerce_platform)
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
