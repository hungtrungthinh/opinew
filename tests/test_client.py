import json
import os
from flask import url_for
from freezegun import freeze_time
from unittest import TestCase
from webapp import create_app, db
from webapp.models import User, Role, Shop
from config import Constants, TestingConstants, basedir
import sensitive
from repopulate import import_tables


class TestFlaskApplication(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app('testing')
        cls.client = cls.app.test_client()
        cls.app.app_context().push()
        try:
            os.remove(cls.app.config.get('DATABASE_LOCATION'))
        except OSError:
            pass
        db.create_all()

        db_dir = os.path.join(basedir, 'install', 'db', cls.app.config.get('MODE'))
        import_tables(db,db_dir)

        admin_role = Role.query.filter_by(name=Constants.ADMIN_ROLE).first()
        cls.admin_user = User.query.filter_by(id=1).first()
        assert admin_role in cls.admin_user.roles
        cls.admin_password = sensitive.ADMIN_PASSWORD

        reviewer_role = Role.query.filter_by(name=Constants.REVIEWER_ROLE).first()
        cls.reviewer_user = User.query.filter_by(id=2).first()
        assert cls.reviewer_user.has_role(reviewer_role)
        cls.reviewer_password = sensitive.TEST_REVIEWER_PASSWORD

        shop_owner_role = Role.query.filter_by(name=Constants.SHOP_OWNER_ROLE).first()
        cls.shop_onwer_user = User.query.filter_by(id=3).first()
        assert cls.shop_onwer_user.has_role(shop_owner_role)
        cls.shop_owner_password = sensitive.TEST_SHOP_OWNER_PASSWORD

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()

    def login(self, email, password):
        return self.client.post('/login', data=dict(
            email=email,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)


class TestViews(TestFlaskApplication):
    def test_public_urls(self):
        for rule in self.app.url_map.iter_rules():
            # Filter out rules we can't navigate to in a browser
            # and rules that require parameters
            if "GET" in rule.methods:
                if rule.endpoint in ['static', 'admin.static', 'security.reset_password']:
                    continue
                url = url_for(rule.endpoint, **(rule.defaults or {}))
                if 'admin' in url:
                    continue
                self.client.get(url, follow_redirects=True)

    def test_shopify_install_no_shop(self):
        response_actual = self.client.get("/install", query_string={'ref': 'shopify'})
        response_expected = {"error": "shop parameter is required"}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_shopify_install_no_shop_domain(self):
        response_actual = self.client.get("/install", query_string={'ref': 'shopify',
                                                                    'shop': '123'})
        response_expected = {"error": 'invalid shop domain'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_shopify_install_incorrect_shop_name(self):
        response_actual = self.client.get("/install", query_string={'ref': 'shopify',
                                                                    'shop': '123456789123456789'})
        response_expected = {"error": 'incorrect shop name'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_shopify_install_shop_exists_and_token(self):
        shop = Shop.query.filter_by(name='Opinew shop').first()
        old_shop_domain = shop.domain
        shop.domain = TestingConstants.NEW_SHOP_DOMAIN
        shop.access_token = 'Hellotoken'
        db.session.add(shop)
        db.session.commit()
        response_actual = self.client.get("/install", query_string={'ref': 'shopify',
                                                                    'shop': shop.domain})
        location_expected = url_for('client.shop_dashboard')
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)
        shop.access_token = None
        shop.domain = old_shop_domain
        db.session.add(shop)
        db.session.commit()

    def test_shopify_install_redirect(self):
        response_actual = self.client.get("/install", query_string={'ref': 'shopify',
                                                                    'shop': TestingConstants.NEW_SHOP_DOMAIN})
        location_expected = 'https://opinew-testing.myshopify.com/admin/oauth/authorize?client_id=7260cb38253b9adc4af0c90eb622f4ce&scope=read_products,read_orders,read_fulfillments&redirect_uri=http://localhost:5000/oauth/callback&state=opinew-testing'
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)

    def test_oauth_callback_no_state(self):
        response_actual = self.client.get("/oauth/callback")
        response_expected = {u'error': u'state parameter is required'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_no_hmac(self):
        response_actual = self.client.get("/oauth/callback", query_string={'state': 'opinew-testing'})
        response_expected = {u'error': u'hmac parameter is required'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_no_shop(self):
        response_actual = self.client.get("/oauth/callback", query_string={'state': 'opinew-testing',
                                                                           'hmac': 'fdsa'})
        response_expected = {u'error': u'shop parameter is required'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_no_code(self):
        response_actual = self.client.get("/oauth/callback", query_string={'state': 'opinew-testing',
                                                                           'hmac': 'fdsa',
                                                                           'shop': TestingConstants.NEW_SHOP_DOMAIN})
        response_expected = {u'error': u'code parameter is required'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_wrong_nonce(self):
        response_actual = self.client.get("/oauth/callback", query_string={'state': 'WRONG_NONCE',
                                                                           'hmac': 'fdsa',
                                                                           'shop': TestingConstants.NEW_SHOP_DOMAIN,
                                                                           'code': 'abc'})
        response_expected = {u'error': u'incorrect nonce'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_no_signature(self):
        response_actual = self.client.get("/oauth/callback", query_string={'state': 'opinew-testing',
                                                                           'hmac': 'fdsa',
                                                                           'shop': TestingConstants.NEW_SHOP_DOMAIN,
                                                                           'code': 'abc'})
        response_expected = {u'error': u'signature required'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_hmac_wrong(self):
        response_actual = self.client.get("/oauth/callback", query_string={'state': 'opinew-testing',
                                                                           'hmac': 'fdsa',
                                                                           'shop': TestingConstants.NEW_SHOP_DOMAIN,
                                                                           'code': 'abc',
                                                                           'signature': 'abc'})
        response_expected = {u'error': u'hmac unverified'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_success(self):
        response_actual = self.client.get("/oauth/callback", query_string={'state': 'opinew-testing',
                                                                           'hmac': '4989858235c2ceded8d751658b9a8d7af995343950bcf65bee49ea48fb20380e',
                                                                           'shop': TestingConstants.NEW_SHOP_DOMAIN,
                                                                           'code': 'abc',
                                                                           'signature': 'abc'})
        location_expected = url_for('client.shop_dashboard')
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)

        new_user = User.query.filter_by(email=TestingConstants.NEW_USER_EMAIL).first()
        new_shop = Shop.query.filter_by(name=TestingConstants.NEW_SHOP_NAME).first()

        self.assertTrue(new_user is not None)
        self.assertTrue(new_shop is not None)
        self.assertEquals(new_user.name, TestingConstants.NEW_USER_NAME)
        self.assertEquals(new_user.roles[0], Constants.SHOP_OWNER_ROLE)
        self.assertEquals(new_shop.owner, new_user)

        db.session.delete(new_user)
        db.session.delete(new_shop)
        db.session.commit()

    def test_register_get(self):
        response_actual = self.client.get("/register")
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h1>Sign Up</h1>' in response_actual.data)

    def test_register_post_empty(self):
        response_actual = self.client.post("/register")
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('This field is required.' in response_actual.data)
        self.assertTrue('Email not provided' in response_actual.data)
        self.assertTrue('Password not provided' in response_actual.data)

    def test_register_post_name(self):
        response_actual = self.client.post("/register", data={'name': TestingConstants.NEW_USER_NAME})
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Email not provided' in response_actual.data)
        self.assertTrue('Password not provided' in response_actual.data)

    def test_register_post_name_and_email(self):
        response_actual = self.client.post("/register", data={'name': TestingConstants.NEW_USER_NAME,
                                                              'email': TestingConstants.NEW_USER_EMAIL})
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Password not provided' in response_actual.data)

    def test_register_post_no_password_confirm(self):
        response_actual = self.client.post("/register", data={'name': TestingConstants.NEW_USER_NAME,
                                                              'email': TestingConstants.NEW_USER_EMAIL,
                                                              'password': TestingConstants.NEW_USER_PWD})
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Passwords do not match' in response_actual.data)

    def test_register_post_not_matching_passwords(self):
        response_actual = self.client.post("/register", data={'name': TestingConstants.NEW_USER_NAME,
                                                              'email': TestingConstants.NEW_USER_EMAIL,
                                                              'password': TestingConstants.NEW_USER_PWD,
                                                              'password_confirm': 'not matching'})
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Passwords do not match' in response_actual.data)

    def test_register_post_default_reviewer(self):
        response_actual = self.client.post("/register", data={'name': TestingConstants.NEW_USER_NAME,
                                                              'email': TestingConstants.NEW_USER_EMAIL,
                                                              'password': TestingConstants.NEW_USER_PWD,
                                                              'password_confirm': TestingConstants.NEW_USER_PWD})
        location_expected = url_for('client.index')
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)

        new_user = User.query.filter_by(email=TestingConstants.NEW_USER_EMAIL).first()

        self.assertTrue(new_user is not None)
        self.assertEquals(new_user.name, TestingConstants.NEW_USER_NAME)
        self.assertEquals(new_user.roles[0], Constants.REVIEWER_ROLE)

        db.session.delete(new_user)
        db.session.commit()

    def test_register_post_shop_owner(self):
        response_actual = self.client.post("/register", data={'name': TestingConstants.NEW_USER_NAME,
                                                              'email': TestingConstants.NEW_USER_EMAIL,
                                                              'password': TestingConstants.NEW_USER_PWD,
                                                              'password_confirm': TestingConstants.NEW_USER_PWD,
                                                              'is_shop_owner': True})
        location_expected = url_for('client.index')
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)

        new_user = User.query.filter_by(email=TestingConstants.NEW_USER_EMAIL).first()

        self.assertTrue(new_user is not None)
        self.assertEquals(new_user.name, TestingConstants.NEW_USER_NAME)
        self.assertEquals(new_user.roles[0], Constants.SHOP_OWNER_ROLE)

        db.session.delete(new_user)
        db.session.commit()

    def test_get_index(self):
        response_actual = self.client.get("/")
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h1>Opinew - Photo Product Reviews</h1>' in response_actual.data)

    def test_get_index_admin(self):
        self.login(self.admin_user.email, self.admin_password)
        response_actual = self.client.get("/")
        location_expected = 'http://' + self.app.config.get('SERVER_NAME') + '/admin'
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)
        self.logout()

    def test_get_index_shop_owner(self):
        self.login(self.shop_onwer_user.email, self.shop_owner_password)
        response_actual = self.client.get("/")
        location_expected = url_for('client.shop_dashboard')
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)
        self.logout()

    def test_get_index_reviewer(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.client.get("/")
        location_expected = url_for('client.reviews')
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)
        self.logout()

    def test_get_reviews(self):
        response_actual = self.client.get("/reviews")
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Business owner?' in response_actual.data)
        self.assertTrue('<b>Opinew shop</b>' in response_actual.data)

    def test_access_admin_home(self):
        self.login(self.admin_user.email, self.admin_password)
        response_actual = self.client.get("/admin/", follow_redirects=True)
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h1>Welcome to admin panel</h1>' in response_actual.data)
        self.logout()

    def test_render_add_review_no_product(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.client.get("/add_review")
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Select product' in response_actual.data)
        self.logout()

    def test_render_add_review_to_product(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.client.get("/add_review", query_string={"product_id": 1})
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h1>Review Ear rings' in response_actual.data)
        self.logout()

    # API
    @freeze_time("2015-03-14")
    def test_api_post_review(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        body_payload = "fdsa"
        payload = json.dumps({"product_id": "1",
                              "star_rating": "4",
                              "body": body_payload})
        response_actual = self.client.post("/api/v1/review",
                                           headers={'content-type': 'application/json'},
                                           data=payload)
        self.assertEquals(response_actual.status_code, 201)
        self.assertTrue(body_payload in response_actual.data)
        self.logout()
