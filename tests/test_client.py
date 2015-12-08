import json
import base64
import hmac
import hashlib
import datetime
import pytz
from dateutil import parser as date_parser
from freezegun import freeze_time
from flask import url_for
from flask.ext.security.utils import verify_password
from webapp import db
from webapp.models import User, Shop, Product, Order
from tests import testing_constants
from config import Constants
from tests.framework import TestFlaskApplication, expect_mail
from config import Config


class TestClient(TestFlaskApplication):
    def test_public_urls(self):
        for rule in self.app.url_map.iter_rules():
            # Filter out rules we can't navigate to in a browser
            # and rules that require parameters
            if "GET" in rule.methods:
                if rule.endpoint in ['static', 'admin.static', 'security.reset_password']:
                    continue
                if rule.endpoint in ['security.confirm_email']:
                    continue
                url = url_for(rule.endpoint, **(rule.defaults or {}))
                if 'admin' in url:
                    continue
                self.desktop_client.get(url, follow_redirects=True)

    def test_shopify_install_no_shop(self):
        response_actual = self.desktop_client.get("/install", query_string={'ref': 'shopify'})
        response_expected = {"error": "shop parameter is required"}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_shopify_install_no_shop_domain(self):
        response_actual = self.desktop_client.get("/install", query_string={'ref': 'shopify',
                                                                            'shop': '123'})
        response_expected = {"error": 'invalid shop domain'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_shopify_install_incorrect_shop_name(self):
        response_actual = self.desktop_client.get("/install", query_string={'ref': 'shopify',
                                                                            'shop': '123456789123456789'})
        response_expected = {"error": 'incorrect shop name'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_shopify_install_redirect(self):
        response_actual = self.desktop_client.get("/install", query_string={'ref': 'shopify',
                                                                            'shop': testing_constants.NEW_SHOP_DOMAIN})
        location_expected = 'https://opinew-testing.myshopify.com/admin/oauth/authorize?client_id=7260cb38253b9adc4af0c90eb622f4ce&scope=read_products,read_orders,read_fulfillments&redirect_uri=http://localhost:5000/oauth/callback&state=opinew-testing'
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)

    def test_oauth_callback_no_state(self):
        response_actual = self.desktop_client.get("/oauth/callback")
        response_expected = {u'error': u'state parameter is required'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_no_hmac(self):
        response_actual = self.desktop_client.get("/oauth/callback", query_string={'state': 'opinew-testing'})
        response_expected = {u'error': u'hmac parameter is required'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_no_shop(self):
        response_actual = self.desktop_client.get("/oauth/callback", query_string={'state': 'opinew-testing',
                                                                                   'hmac': 'fdsa'})
        response_expected = {u'error': u'shop parameter is required'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_no_code(self):
        response_actual = self.desktop_client.get("/oauth/callback", query_string={'state': 'opinew-testing',
                                                                                   'hmac': 'fdsa',
                                                                                   'shop': testing_constants.NEW_SHOP_DOMAIN})
        response_expected = {u'error': u'code parameter is required'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_wrong_nonce(self):
        response_actual = self.desktop_client.get("/oauth/callback", query_string={'state': 'WRONG_NONCE',
                                                                                   'hmac': 'fdsa',
                                                                                   'shop': testing_constants.NEW_SHOP_DOMAIN,
                                                                                   'code': 'abc'})
        response_expected = {u'error': u'incorrect nonce'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_no_signature(self):
        response_actual = self.desktop_client.get("/oauth/callback", query_string={'state': 'opinew-testing',
                                                                                   'hmac': 'fdsa',
                                                                                   'shop': testing_constants.NEW_SHOP_DOMAIN,
                                                                                   'code': 'abc'})
        response_expected = {u'error': u'signature required'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_hmac_wrong(self):
        response_actual = self.desktop_client.get("/oauth/callback", query_string={'state': 'opinew-testing',
                                                                                   'hmac': 'fdsa',
                                                                                   'shop': testing_constants.NEW_SHOP_DOMAIN,
                                                                                   'code': 'abc',
                                                                                   'signature': 'abc'})
        response_expected = {u'error': u'hmac unverified'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_register_get(self):
        response_actual = self.desktop_client.get("/register")
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h1>Register' in response_actual.data)

    def test_register_post_empty(self):
        response_actual = self.desktop_client.post("/register")
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('This field is required.' in response_actual.data)
        self.assertTrue('Email not provided' in response_actual.data)
        self.assertTrue('Password not provided' in response_actual.data)

    def test_register_post_name(self):
        response_actual = self.desktop_client.post("/register", data={'name': testing_constants.NEW_USER_NAME})
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Email not provided' in response_actual.data)
        self.assertTrue('Password not provided' in response_actual.data)

    def test_register_post_name_and_email(self):
        response_actual = self.desktop_client.post("/register", data={'name': testing_constants.NEW_USER_NAME,
                                                                      'email': testing_constants.NEW_USER_EMAIL})
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Password not provided' in response_actual.data)

    def test_register_post_no_password_confirm(self):
        response_actual = self.desktop_client.post("/register", data={'name': testing_constants.NEW_USER_NAME,
                                                                      'email': testing_constants.NEW_USER_EMAIL,
                                                                      'password': testing_constants.NEW_USER_PWD})
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Passwords do not match' in response_actual.data)

    def test_register_post_not_matching_passwords(self):
        response_actual = self.desktop_client.post("/register", data={'name': testing_constants.NEW_USER_NAME,
                                                                      'email': testing_constants.NEW_USER_EMAIL,
                                                                      'password': testing_constants.NEW_USER_PWD,
                                                                      'password_confirm': 'not matching'})
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Passwords do not match' in response_actual.data)

    @expect_mail
    def test_register_post_default_reviewer(self):
        response_actual = self.desktop_client.post("/register", data={'name': testing_constants.NEW_USER_NAME,
                                                                      'email': testing_constants.NEW_USER_EMAIL,
                                                                      'password': testing_constants.NEW_USER_PWD,
                                                                      'password_confirm': testing_constants.NEW_USER_PWD})
        location_expected = 'http://localhost:5000/confirm'
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)

        new_user = User.query.filter_by(email=testing_constants.NEW_USER_EMAIL).first()

        self.assertTrue(new_user is not None)
        self.assertEquals(new_user.name, testing_constants.NEW_USER_NAME)
        self.assertEquals(new_user.roles[0], Constants.REVIEWER_ROLE)

        # TODO: check email
        self.assertEquals(len(self.outbox), 1)

        db.session.delete(new_user)
        db.session.commit()

    def test_register_post_shop_owner(self):
        response_actual = self.desktop_client.post("/register", data={'name': testing_constants.NEW_USER_NAME,
                                                                      'email': testing_constants.NEW_USER_EMAIL,
                                                                      'password': testing_constants.NEW_USER_PWD,
                                                                      'password_confirm': testing_constants.NEW_USER_PWD,
                                                                      'is_shop_owner': True})
        location_expected = 'http://localhost:5000/confirm'
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)

        new_user = User.query.filter_by(email=testing_constants.NEW_USER_EMAIL).first()

        self.assertTrue(new_user is not None)
        self.assertEquals(new_user.name, testing_constants.NEW_USER_NAME)
        self.assertEquals(new_user.roles[0], Constants.SHOP_OWNER_ROLE)

        db.session.delete(new_user)
        db.session.commit()

    def test_get_index(self):
        response_actual = self.desktop_client.get("/")
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h1>Opinew - Photo Product Reviews</h1>' in response_actual.data)

    def test_get_index_admin(self):
        self.login(self.admin_user.email, self.admin_password)
        response_actual = self.desktop_client.get("/")
        location_expected = 'http://' + self.app.config.get('SERVER_NAME') + '/admin'
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)
        self.logout()

    def test_get_index_shop_owner(self):
        self.login(self.shop_owner_user.email, self.shop_owner_password)
        response_actual = self.desktop_client.get("/")
        location_expected = url_for('client.shop_dashboard')
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)
        self.logout()

    def test_get_index_reviewer(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.desktop_client.get("/")
        location_expected = url_for('client.user_profile', user_id=self.reviewer_user.id)
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)
        self.logout()

    def test_get_index_mobile(self):
        response_actual = self.mobile_client.get("/")
        location_expected = url_for('client.reviews')
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)

    def test_get_index_mobile_logged_in(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.mobile_client.get("/")
        location_expected = url_for('client.user_profile', user_id=self.reviewer_user.id)
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)
        self.logout()

    ##
    def test_get_index_mobile_not_logged_in_reviews(self):
        response_actual = self.mobile_client.get(url_for('client.reviews'))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<footer' not in response_actual.data)

    def test_get_index_mobile_product_page(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.mobile_client.get(url_for('client.get_product', product_id=1))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Review' in response_actual.data)
        self.logout()

    def test_get_index_mobile_add_review(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.mobile_client.get(url_for('client.reviews'))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('take a picture' not in response_actual.data)
        self.logout()

    def test_get_reviews(self):
        response_actual = self.desktop_client.get("/reviews")
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Business owner?' in response_actual.data)
        self.assertTrue('<b>Opinew shop</b>' in response_actual.data)

    def test_user_profile(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.desktop_client.get("/user-profile/" + str(self.reviewer_user.id))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h3>Rose Castro' in response_actual.data)
        self.assertTrue('Great value for money yoga mat' in response_actual.data)
        self.assertTrue('Reviews: 2' in response_actual.data)
        self.assertTrue('Likes: 0' in response_actual.data)
        self.logout()

    def test_access_admin_home(self):
        self.login(self.admin_user.email, self.admin_password)
        response_actual = self.desktop_client.get("/admin/", follow_redirects=True)
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h1>Welcome to admin panel' in response_actual.data)
        self.logout()

    def test_dashboard(self):
        self.login(self.shop_owner_user.email, self.shop_owner_password)
        response_actual = self.desktop_client.get("/dashboard/2", follow_redirects=True)
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('General settings' in response_actual.data)
        self.assertTrue('Orders' in response_actual.data)
        self.assertTrue('Reviews' in response_actual.data)
        self.logout()

    def test_dashboard_orders(self):
        self.login(self.shop_owner_user.email, self.shop_owner_password)
        response_actual = self.desktop_client.get("/dashboard/2/orders", follow_redirects=True)
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h2>Orders</h2>' in response_actual.data)
        self.logout()

    def test_dashboard_reviews(self):
        self.login(self.shop_owner_user.email, self.shop_owner_password)
        response_actual = self.desktop_client.get("/dashboard/2/reviews", follow_redirects=True)
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h2>Reviews</h2>' in response_actual.data)
        self.logout()

    def test_render_add_review_no_product(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.desktop_client.get(url_for('client.add_review'))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Select product' in response_actual.data)
        self.logout()

    def test_render_add_review_to_product(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.desktop_client.get(url_for('client.add_review'), query_string={"product_id": 1})
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<a href="/product/1">Ear rings</a>' in response_actual.data)
        self.logout()

    def test_plugin_404(self):
        response_actual = self.desktop_client.get(url_for('client.get_plugin'))
        self.assertEquals(response_actual.status_code, 404)
        self.assertEquals('', response_actual.data)

    def test_plugin_get_by_platform_id_not_logged_in(self):
        response_actual = self.desktop_client.get(url_for('client.get_plugin'), query_string=dict(
            shop_id=2, platform_product_id=1, get_by='platform_id'
        ))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h4>See all Ear rings reviews on Opinew</h4>' in response_actual.data)
        self.assertTrue('Perfect unusual accessory for a normal day' in response_actual.data)
        self.assertTrue('Write a review' in response_actual.data)
        self.assertTrue('modal-review' in response_actual.data)

    def test_plugin_get_by_platform_id_logged_in(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.desktop_client.get(url_for('client.get_plugin'), query_string=dict(
            shop_id=2, platform_product_id=1, get_by='platform_id'
        ))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('href="/plugin-logout"' in response_actual.data)
        self.assertTrue('<h4>See all Ear rings reviews on Opinew</h4>' in response_actual.data)
        self.assertTrue('Perfect unusual accessory for a normal day' in response_actual.data)
        self.assertTrue('Write a review' in response_actual.data)
        self.assertTrue('modal-review' in response_actual.data)
        self.assertTrue('Rose Castro' in response_actual.data)
        self.assertTrue('https://opinew.com/media/user/3_rose_castro.jpg' in response_actual.data)
        self.logout()

    def test_plugin_get_by_url_not_logged_in(self):
        response_actual = self.desktop_client.get(url_for('client.get_plugin'), query_string=dict(
            shop_id=2, product_url='opinew_shop.local:5001/product/1', get_by='url'
        ))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h4>See all Ear rings reviews on Opinew</h4>' in response_actual.data)
        self.assertTrue('Perfect unusual accessory for a normal day' in response_actual.data)
        self.assertTrue('Write a review' in response_actual.data)
        self.assertTrue('modal-review' in response_actual.data)

    def test_plugin_get_by_url_regex_not_logged_in(self):
        response_actual = self.desktop_client.get(url_for('client.get_plugin'), query_string=dict(
            shop_id=2, product_url='opinew_shop.local:5001/something_else/product/1', get_by='url'
        ))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h4>See all Ear rings reviews on Opinew</h4>' in response_actual.data)
        self.assertTrue('Perfect unusual accessory for a normal day' in response_actual.data)
        self.assertTrue('Write a review' in response_actual.data)
        self.assertTrue('modal-review' in response_actual.data)

    def test_plugin_get_by_url_logged_in(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.desktop_client.get(url_for('client.get_plugin'), query_string=dict(
            shop_id=2, product_url='opinew_shop.local:5001/product/1', get_by='url'
        ))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('href="/plugin-logout"' in response_actual.data)
        self.assertTrue('<h4>See all Ear rings reviews on Opinew</h4>' in response_actual.data)
        self.assertTrue('Perfect unusual accessory for a normal day' in response_actual.data)
        self.assertTrue('Write a review' in response_actual.data)
        self.assertTrue('modal-review' in response_actual.data)
        self.assertTrue('modal-signup' not in response_actual.data)
        self.assertTrue('Rose Castro' in response_actual.data)
        self.logout()

    def test_shopify_create_product(self):
        data = json.dumps({
            'id': testing_constants.NEW_PRODUCT_PLATFORM_ID,
            'title': testing_constants.NEW_PRODUCT_NAME
        })
        sha256 = base64.b64encode(hmac.new(Config.SHOPIFY_APP_SECRET, msg=data, digestmod=hashlib.sha256).digest())
        response_actual = self.desktop_client.post(url_for('api.platform_shopify_create_product'),
                                                   data=data,
                                                   content_type="application/json",
                                                   headers={
                                                       'X-Shopify-Hmac-SHA256': sha256,
                                                       'X-Shopify-Shop-Domain': testing_constants.SHOPIFY_SHOP_DOMAIN})
        self.assertEquals(response_actual.status_code, 201)
        product = Product.query.filter_by(platform_product_id=testing_constants.NEW_PRODUCT_PLATFORM_ID,
                                          shop_id=testing_constants.SHOPIFY_SHOP_ID).first()
        location_expected = url_for('client.get_product', product_id=product.id)
        self.assertEquals(location_expected, response_actual.headers.get('Location'))
        self.assertEquals(product.name, testing_constants.NEW_PRODUCT_NAME)
        db.session.delete(product)
        db.session.commit()

    def test_shopify_update_product(self):
        product = Product(platform_product_id=testing_constants.NEW_PRODUCT_PLATFORM_ID,
                          name=testing_constants.NEW_PRODUCT_NAME,
                          shop_id=testing_constants.SHOPIFY_SHOP_ID)
        db.session.add(product)
        db.session.commit()
        data = json.dumps({
            'id': testing_constants.NEW_PRODUCT_PLATFORM_ID,
            'title': testing_constants.CHANGED_PRODUCT_NAME
        })
        sha256 = base64.b64encode(hmac.new(Config.SHOPIFY_APP_SECRET, msg=data, digestmod=hashlib.sha256).digest())
        response_actual = self.desktop_client.post(url_for('api.platform_shopify_update_product'),
                                                   data=data,
                                                   content_type="application/json",
                                                   headers={
                                                       'X-Shopify-Hmac-SHA256': sha256,
                                                       'X-Shopify-Shop-Domain': testing_constants.SHOPIFY_SHOP_DOMAIN})
        self.assertEquals(response_actual.status_code, 200)
        product = Product.query.filter_by(platform_product_id=testing_constants.NEW_PRODUCT_PLATFORM_ID,
                                          shop_id=testing_constants.SHOPIFY_SHOP_ID).first()
        self.assertEquals(product.name, testing_constants.CHANGED_PRODUCT_NAME)
        db.session.delete(product)
        db.session.commit()

    def test_shopify_delete_product(self):
        product = Product(platform_product_id=testing_constants.NEW_PRODUCT_PLATFORM_ID,
                          name=testing_constants.NEW_PRODUCT_NAME,
                          shop_id=testing_constants.SHOPIFY_SHOP_ID)
        db.session.add(product)
        db.session.commit()
        data = json.dumps({
            'id': testing_constants.NEW_PRODUCT_PLATFORM_ID,
        })
        sha256 = base64.b64encode(hmac.new(Config.SHOPIFY_APP_SECRET, msg=data, digestmod=hashlib.sha256).digest())
        response_actual = self.desktop_client.post(url_for('api.platform_shopify_delete_product'),
                                                   data=data,
                                                   headers={
                                                       'X-Shopify-Hmac-SHA256': sha256,
                                                       'X-Shopify-Shop-Domain': testing_constants.SHOPIFY_SHOP_DOMAIN})
        self.assertEquals(response_actual.status_code, 200)
        product = Product.query.filter_by(platform_product_id=testing_constants.NEW_PRODUCT_PLATFORM_ID,
                                          shop_id=testing_constants.SHOPIFY_SHOP_ID).first()
        self.assertIsNone(product)

    def test_shopify_create_order(self):
        product = Product(platform_product_id=testing_constants.NEW_PRODUCT_PLATFORM_ID,
                          name=testing_constants.NEW_PRODUCT_NAME,
                          shop_id=testing_constants.SHOPIFY_SHOP_ID)
        db.session.add(product)
        db.session.commit()
        data = json.dumps({
            'id': testing_constants.NEW_ORDER_PLATFORM_ID,
            'customer': {
                'email': testing_constants.ORDER_USER_EMAIL
            },
            'line_items': [
                {
                    'product_id': testing_constants.NEW_PRODUCT_PLATFORM_ID
                }
            ]
        })
        sha256 = base64.b64encode(hmac.new(Config.SHOPIFY_APP_SECRET, msg=data, digestmod=hashlib.sha256).digest())
        response_actual = self.desktop_client.post(url_for('api.platform_shopify_create_order'),
                                                   data=data,
                                                   headers={
                                                       'X-Shopify-Hmac-SHA256': sha256,
                                                       'X-Shopify-Shop-Domain': testing_constants.SHOPIFY_SHOP_DOMAIN})
        self.assertEquals(response_actual.status_code, 201)
        product = Product.query.filter_by(platform_product_id=testing_constants.NEW_PRODUCT_PLATFORM_ID,
                                          shop_id=testing_constants.SHOPIFY_SHOP_ID).first()
        order = Order.query.filter_by(platform_order_id=testing_constants.NEW_ORDER_PLATFORM_ID,
                                      shop_id=testing_constants.SHOPIFY_SHOP_ID).first()
        self.assertEquals(order.user_legacy.email, testing_constants.ORDER_USER_EMAIL)
        self.assertIn(product, order.products)
        db.session.delete(order)
        db.session.delete(product)
        db.session.commit()

    @freeze_time(testing_constants.ORDER_NOW)
    def test_shopify_fulfill_order(self):
        order = Order(platform_order_id=testing_constants.NEW_ORDER_PLATFORM_ID,
                      shop_id=testing_constants.SHOPIFY_SHOP_ID)
        db.session.add(order)
        db.session.commit()
        data = json.dumps({
            'order_id': testing_constants.NEW_ORDER_PLATFORM_ID,
            'tracking_number': testing_constants.ORDER_TRACKING_NUMBER,
            'created_at': testing_constants.ORDER_SHIPPED_AT
        })
        sha256 = base64.b64encode(hmac.new(Config.SHOPIFY_APP_SECRET, msg=data, digestmod=hashlib.sha256).digest())
        response_actual = self.desktop_client.post(url_for('api.platform_shopify_fulfill_order'),
                                                   data=data,
                                                   headers={
                                                       'X-Shopify-Hmac-SHA256': sha256,
                                                       'X-Shopify-Shop-Domain': testing_constants.SHOPIFY_SHOP_DOMAIN})
        self.assertEquals(response_actual.status_code, 200)
        order = Order.query.filter_by(platform_order_id=testing_constants.NEW_ORDER_PLATFORM_ID,
                                      shop_id=testing_constants.SHOPIFY_SHOP_ID).first()
        self.assertEquals(order.status, Constants.ORDER_STATUS_NOTIFIED)
        db.session.delete(order)
        db.session.commit()

    def test_password_change_get(self):
        self.login(self.shop_owner_user.email, self.shop_owner_password)
        response_actual = self.desktop_client.get("/change")
        self.assertTrue('<h2>Change password</h2>' in response_actual.data)
        self.logout()

    @expect_mail
    def test_password_change_post(self):
        self.login(self.shop_owner_user.email, self.shop_owner_password)
        old_pwd_hash = self.shop_owner_user.password
        response_actual = self.desktop_client.post("/change", data={'password': self.shop_owner_password,
                                                                    'new_password': testing_constants.CHANGED_PASSWORD,
                                                                    'new_password_confirm': testing_constants.CHANGED_PASSWORD})
        location_expected = url_for('client.post_change')
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)
        self.assertTrue(verify_password(testing_constants.CHANGED_PASSWORD, self.shop_owner_user.password))
        # TODO check email contents
        self.assertEquals(len(self.outbox), 1)
        # change back
        self.shop_owner_user.password = old_pwd_hash
        db.session.add(self.shop_owner_user)
        db.session.commit()
        # verify change back
        self.assertTrue(verify_password(self.shop_owner_password, self.shop_owner_user.password))
        self.logout()

    def test_two_shops_per_user(self):
        self.login(self.shop_owner_user.email, self.shop_owner_password)
        # create new shop for this user
        new_shop = Shop(name=testing_constants.NEW_SHOP_NAME)
        self.shop_owner_user.shops.append(new_shop)
        db.session.add(new_shop)
        db.session.commit()
        # check if the dashboard is rendered correctly
        response_actual = self.desktop_client.get(url_for('client.shop_dashboard'))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h2>Please choose a shop to administrate:</h2>' in response_actual.data)
        self.assertTrue(testing_constants.NEW_SHOP_NAME in response_actual.data)
        # delete this shop
        db.session.delete(new_shop)
        db.session.commit()
        self.logout()

    def test_plugin_is_invalid_after_trial(self):
        old_confirmed_at = self.shop_owner_user.confirmed_at
        # set 1 day after expiry
        self.shop_owner_user.confirmed_at = datetime.datetime.utcnow() - datetime.timedelta(
            days=Constants.TRIAL_PERIOD_DAYS + 1)
        self.assertTrue(self.shop_owner_user.customer[0].last4 is None)
        db.session.add(self.shop_owner_user)
        db.session.commit()
        # test
        response_actual = self.desktop_client.get(url_for('client.get_plugin'), query_string=dict(
            shop_id=2, product_url='opinew_shop.local:5001/product/1', get_by='url'
        ))
        self.assertEquals(response_actual.status_code, 404)
        self.assertTrue(response_actual.data == '')
        # revert
        self.shop_owner_user.confirmed_at = old_confirmed_at
        db.session.add(self.shop_owner_user)
        db.session.commit()

    def test_dashboard_trial_expiry_in_26_days(self):
        old_confirmed_at = self.shop_owner_user.confirmed_at
        # set 1 day after expiry
        self.shop_owner_user.confirmed_at = datetime.datetime.utcnow() - datetime.timedelta(days=Constants.TRIAL_PERIOD_DAYS - 27)
        self.assertTrue(self.shop_owner_user.customer[0].last4 is None)
        db.session.add(self.shop_owner_user)
        db.session.commit()
        # test
        self.login(self.shop_owner_user.email, self.shop_owner_password)
        response_actual = self.desktop_client.get("/dashboard/2", follow_redirects=True)
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Your trial expires in 26 days' in response_actual.data)
        self.logout()
        # revert
        self.shop_owner_user.confirmed_at = old_confirmed_at
        db.session.add(self.shop_owner_user)
        db.session.commit()

    def test_dashboard_trial_expired(self):
        old_confirmed_at = self.shop_owner_user.confirmed_at
        # set 1 day after expiry
        self.shop_owner_user.confirmed_at = datetime.datetime.utcnow() - datetime.timedelta(days=Constants.TRIAL_PERIOD_DAYS + 1)
        self.assertTrue(self.shop_owner_user.customer[0].last4 is None)
        db.session.add(self.shop_owner_user)
        db.session.commit()
        # test
        self.login(self.shop_owner_user.email, self.shop_owner_password)
        response_actual = self.desktop_client.get("/dashboard/2", follow_redirects=True)
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Your trial has expired!' in response_actual.data)
        self.logout()
        # revert
        self.shop_owner_user.confirmed_at = old_confirmed_at
        db.session.add(self.shop_owner_user)
        db.session.commit()
