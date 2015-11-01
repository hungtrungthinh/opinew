import json
import os
import datetime
from flask import url_for
from freezegun import freeze_time
from unittest import TestCase
from webapp import create_app, db
from webapp.models import User, Role, Shop, Review
from tests import testing_constants
from config import Constants, basedir
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
        shop.domain = testing_constants.NEW_SHOP_DOMAIN
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
                                                                    'shop': testing_constants.NEW_SHOP_DOMAIN})
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
                                                                           'shop': testing_constants.NEW_SHOP_DOMAIN})
        response_expected = {u'error': u'code parameter is required'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_wrong_nonce(self):
        response_actual = self.client.get("/oauth/callback", query_string={'state': 'WRONG_NONCE',
                                                                           'hmac': 'fdsa',
                                                                           'shop': testing_constants.NEW_SHOP_DOMAIN,
                                                                           'code': 'abc'})
        response_expected = {u'error': u'incorrect nonce'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_no_signature(self):
        response_actual = self.client.get("/oauth/callback", query_string={'state': 'opinew-testing',
                                                                           'hmac': 'fdsa',
                                                                           'shop': testing_constants.NEW_SHOP_DOMAIN,
                                                                           'code': 'abc'})
        response_expected = {u'error': u'signature required'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_hmac_wrong(self):
        response_actual = self.client.get("/oauth/callback", query_string={'state': 'opinew-testing',
                                                                           'hmac': 'fdsa',
                                                                           'shop': testing_constants.NEW_SHOP_DOMAIN,
                                                                           'code': 'abc',
                                                                           'signature': 'abc'})
        response_expected = {u'error': u'hmac unverified'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_success(self):
        response_actual = self.client.get("/oauth/callback", query_string={'state': 'opinew-testing',
                                                                           'hmac': '4989858235c2ceded8d751658b9a8d7af995343950bcf65bee49ea48fb20380e',
                                                                           'shop': testing_constants.NEW_SHOP_DOMAIN,
                                                                           'code': 'abc',
                                                                           'signature': 'abc'})
        location_expected = url_for('client.shop_dashboard')
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)

        new_user = User.query.filter_by(email=testing_constants.NEW_USER_EMAIL).first()
        new_shop = Shop.query.filter_by(name=testing_constants.NEW_SHOP_NAME).first()

        self.assertTrue(new_user is not None)
        self.assertTrue(new_shop is not None)
        self.assertEquals(new_user.name, testing_constants.NEW_USER_NAME)
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
        response_actual = self.client.post("/register", data={'name': testing_constants.NEW_USER_NAME})
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Email not provided' in response_actual.data)
        self.assertTrue('Password not provided' in response_actual.data)

    def test_register_post_name_and_email(self):
        response_actual = self.client.post("/register", data={'name': testing_constants.NEW_USER_NAME,
                                                              'email': testing_constants.NEW_USER_EMAIL})
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Password not provided' in response_actual.data)

    def test_register_post_no_password_confirm(self):
        response_actual = self.client.post("/register", data={'name': testing_constants.NEW_USER_NAME,
                                                              'email': testing_constants.NEW_USER_EMAIL,
                                                              'password': testing_constants.NEW_USER_PWD})
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Passwords do not match' in response_actual.data)

    def test_register_post_not_matching_passwords(self):
        response_actual = self.client.post("/register", data={'name': testing_constants.NEW_USER_NAME,
                                                              'email': testing_constants.NEW_USER_EMAIL,
                                                              'password': testing_constants.NEW_USER_PWD,
                                                              'password_confirm': 'not matching'})
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Passwords do not match' in response_actual.data)

    def test_register_post_default_reviewer(self):
        response_actual = self.client.post("/register", data={'name': testing_constants.NEW_USER_NAME,
                                                              'email': testing_constants.NEW_USER_EMAIL,
                                                              'password': testing_constants.NEW_USER_PWD,
                                                              'password_confirm': testing_constants.NEW_USER_PWD})
        location_expected = url_for('client.index')
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)

        new_user = User.query.filter_by(email=testing_constants.NEW_USER_EMAIL).first()

        self.assertTrue(new_user is not None)
        self.assertEquals(new_user.name, testing_constants.NEW_USER_NAME)
        self.assertEquals(new_user.roles[0], Constants.REVIEWER_ROLE)

        db.session.delete(new_user)
        db.session.commit()

    def test_register_post_shop_owner(self):
        response_actual = self.client.post("/register", data={'name': testing_constants.NEW_USER_NAME,
                                                              'email': testing_constants.NEW_USER_EMAIL,
                                                              'password': testing_constants.NEW_USER_PWD,
                                                              'password_confirm': testing_constants.NEW_USER_PWD,
                                                              'is_shop_owner': True})
        location_expected = url_for('client.index')
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)

        new_user = User.query.filter_by(email=testing_constants.NEW_USER_EMAIL).first()

        self.assertTrue(new_user is not None)
        self.assertEquals(new_user.name, testing_constants.NEW_USER_NAME)
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
        response_actual = self.client.get(url_for('client.add_review'))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Select product' in response_actual.data)
        self.logout()

    def test_render_add_review_to_product(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.client.get(url_for('client.add_review'), query_string={"product_id": 1})
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h1>Review Ear rings' in response_actual.data)
        self.logout()

    @freeze_time(testing_constants.NEW_REVIEW_CREATED_TS)
    def test_api_post_review_full_pipeline(self):
        split_frozen_time = testing_constants.NEW_REVIEW_CREATED_TS.split('-')
        frozen_time = datetime.datetime(int(split_frozen_time[0]), int(split_frozen_time[1]), int(split_frozen_time[2]))
        # Login as a reviewer
        self.login(self.reviewer_user.email, self.reviewer_password)
        payload = json.dumps({"product_id": testing_constants.NEW_REVIEW_PRODUCT_ID,
                              "body": testing_constants.NEW_REVIEW_BODY,
                              "star_rating": testing_constants.NEW_REVIEW_STARS,
                              "image_url": testing_constants.NEW_REVIEW_IMAGE_URL})
        response_actual = self.client.post("/api/v1/review",
                                           headers={'content-type': 'application/json'},
                                           data=payload)

        # First, check if API response is good...
        self.assertEquals(response_actual.status_code, 201)
        jsonified_response = json.loads(response_actual.data)
        self.assertTrue('body' in jsonified_response and
                        unicode(testing_constants.NEW_REVIEW_BODY) == jsonified_response['body'])
        self.assertTrue('star_rating' in jsonified_response and
                        testing_constants.NEW_REVIEW_STARS == jsonified_response['star_rating'])
        self.assertTrue('image_url' in jsonified_response and
                        testing_constants.NEW_REVIEW_IMAGE_URL == jsonified_response['image_url'])
        self.assertTrue('product_id' in jsonified_response and
                        testing_constants.NEW_REVIEW_PRODUCT_ID == jsonified_response['product_id'])
        self.assertTrue('password' not in jsonified_response['user'])

        # Check if db records are fine and dandy...
        review_id = jsonified_response['id']
        review = Review.query.filter_by(id=review_id).first()
        self.assertEquals(testing_constants.NEW_REVIEW_BODY, review.body)
        self.assertEquals(testing_constants.NEW_REVIEW_STARS, review.star_rating)
        self.assertEquals(testing_constants.NEW_REVIEW_IMAGE_URL, review.image_url)
        self.assertFalse(review.approval_pending)
        self.assertFalse(review.by_shop_owner)
        self.assertFalse(review.verified_review)
        self.assertEquals(frozen_time, review.created_ts)
        self.assertTrue(review.approved_by_shop)

        # Finally, check that what needs to be rendered, is rendered..
        response_actual = self.client.get(url_for('client.get_product', product_id=1))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue(testing_constants.NEW_REVIEW_BODY in response_actual.data)
        self.assertTrue(testing_constants.NEW_REVIEW_IMAGE_URL in response_actual.data)
        self.assertTrue(testing_constants.RENDERED_STARS in response_actual.data)
        self.logout()

    def helper_api_post_review_youtube_link(self, body_string):
        self.login(self.reviewer_user.email, self.reviewer_password)
        payload = json.dumps({"product_id": testing_constants.NEW_REVIEW_PRODUCT_ID,
                              "body": body_string})
        response_actual = self.client.post("/api/v1/review",
                                           headers={'content-type': 'application/json'},
                                           data=payload)

        # First, check if API response is good...
        self.assertEquals(response_actual.status_code, 201)
        jsonified_response = json.loads(response_actual.data)
        self.assertTrue('body' in jsonified_response and
                        unicode(testing_constants.NEW_REVIEW_BODY) == jsonified_response['body'])

        # Check if db records are fine and dandy...
        review_id = jsonified_response['id']
        review = Review.query.filter_by(id=review_id).first()
        self.assertEquals(testing_constants.NEW_REVIEW_BODY, review.body)
        self.assertEquals(Constants.YOUTUBE_EMBED_URL.format(youtube_video_id=testing_constants.NEW_REVIEW_YOUTUBE_VIDEO_ID), review.youtube_video)

        # Finally, check that what needs to be rendered, is rendered..
        response_actual = self.client.get(url_for('client.get_product', product_id=1))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue(testing_constants.NEW_REVIEW_BODY in response_actual.data)
        self.assertTrue(testing_constants.RENDERED_YOUTUBE in response_actual.data)
        self.logout()

    def test_api_post_review_youtube_link_at_end_of_body(self):
        self.helper_api_post_review_youtube_link(testing_constants.NEW_REVIEW_BODY + ' ' + testing_constants.NEW_REVIEW_YOUTUBE_LINK)

    def test_api_post_review_youtube_link_at_beginning_of_body(self):
        self.helper_api_post_review_youtube_link(testing_constants.NEW_REVIEW_YOUTUBE_LINK + ' ' +testing_constants.NEW_REVIEW_BODY)

    def test_api_post_review_youtube_link_middle_of_body(self):
        self.helper_api_post_review_youtube_link(' ' + testing_constants.NEW_REVIEW_YOUTUBE_LINK + ' ' +testing_constants.NEW_REVIEW_BODY)

    def test_api_post_review_shop_owner(self):
        split_frozen_time = testing_constants.NEW_REVIEW_CREATED_TS.split('-')
        frozen_time = datetime.datetime(int(split_frozen_time[0]), int(split_frozen_time[1]), int(split_frozen_time[2]))
        self.login(self.shop_onwer_user.email, self.shop_owner_password)
        payload = json.dumps({"product_id": testing_constants.NEW_REVIEW_PRODUCT_ID})
        response_actual = self.client.post("/api/v1/review",
                                           headers={'content-type': 'application/json'},
                                           data=payload)

        # First, check if API response is good...
        self.assertEquals(response_actual.status_code, 201)
        jsonified_response = json.loads(response_actual.data)
        self.assertTrue('product_id' in jsonified_response and
                        testing_constants.NEW_REVIEW_PRODUCT_ID == jsonified_response['product_id'])
        self.assertTrue('by_shop_owner' in jsonified_response and jsonified_response['by_shop_owner'])

        # Check if db records are fine and dandy...
        review_id = jsonified_response['id']
        review = Review.query.filter_by(id=review_id).first()
        self.assertTrue(review.by_shop_owner)

        # Finally, check that what needs to be rendered, is rendered..
        response_actual = self.client.get(url_for('client.get_product', product_id=1))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue(testing_constants.RENDERED_BY_SHOP_OWNER in response_actual.data)
        self.logout()

    def test_plugin_404(self):
        response_actual = self.client.get(url_for('client.get_plugin'))
        self.assertEquals(response_actual.status_code, 404)
        self.assertEquals('', response_actual.data)

    def test_plugin_get_by_platform_id_not_logged_in(self):
        response_actual = self.client.get(url_for('client.get_plugin'), query_string=dict(
            shop_id=2, platform_product_id=1, get_by='platform_id'
        ))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h2>Ear rings Reviews</h2>' in response_actual.data)
        self.assertTrue('Perfect unusual accessory for a normal day' in response_actual.data)
        self.assertTrue('Write a review' in response_actual.data)
        self.assertTrue('modal-review' not in response_actual.data)
        self.assertTrue('modal-signup' in response_actual.data)

    def test_plugin_get_by_platform_id_logged_in(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.client.get(url_for('client.get_plugin'), query_string=dict(
            shop_id=2, platform_product_id=1, get_by='platform_id'
        ))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h2>Ear rings Reviews</h2>' in response_actual.data)
        self.assertTrue('Perfect unusual accessory for a normal day' in response_actual.data)
        self.assertTrue('Write a review' in response_actual.data)
        self.assertTrue('modal-review' in response_actual.data)
        self.assertTrue('modal-signup' not in response_actual.data)
        self.assertTrue('Rose Castro' in response_actual.data)
        self.assertTrue('https://opinew.com/media/user/3_rose_castro.jpg' in response_actual.data)
        self.logout()

    def test_plugin_get_by_loc_not_logged_in(self):
        response_actual = self.client.get(url_for('client.get_plugin'), query_string=dict(
            shop_id=2, product_location='http://opinew_shop.local:5001/product/1', get_by='loc'
        ))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h2>Ear rings Reviews</h2>' in response_actual.data)
        self.assertTrue('Perfect unusual accessory for a normal day' in response_actual.data)
        self.assertTrue('Write a review' in response_actual.data)
        self.assertTrue('modal-review' not in response_actual.data)
        self.assertTrue('modal-signup' in response_actual.data)

    def test_plugin_get_by_loc_logged_in(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.client.get(url_for('client.get_plugin'), query_string=dict(
            shop_id=2, product_location='http://opinew_shop.local:5001/product/1', get_by='loc'
        ))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h2>Ear rings Reviews</h2>' in response_actual.data)
        self.assertTrue('Perfect unusual accessory for a normal day' in response_actual.data)
        self.assertTrue('Write a review' in response_actual.data)
        self.assertTrue('modal-review' in response_actual.data)
        self.assertTrue('modal-signup' not in response_actual.data)
        self.assertTrue('Rose Castro' in response_actual.data)
        self.logout()
