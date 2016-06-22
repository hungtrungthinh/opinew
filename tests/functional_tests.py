# -*- coding: utf-8 -*-
import json
import base64
import hmac
import hashlib
import httplib
from freezegun import freeze_time
from flask import url_for
from webapp import db
from webapp.models import Shop, Product, Order
from tests import testing_constants
from webapp.exceptions import ExceptionMessages
from tests.framework import TestFlaskApplication, expect_mail
from config import Config, Constants


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


class TestShopifyPluginInstall(TestFlaskApplication):
    """
    Can a shop install the plugin?
    Is it fast and easy to set up?
    Is it easy to ask for help?
    Do we get all the products? Orders? Users?
    Do we render the plugin correctly?
    """

    def test_shopify_install_no_shop(self):
        response_actual = self.desktop_client.get("/platforms/shopify/shops/install")
        response_expected = {u'error': ExceptionMessages.MISSING_PARAM.format(param='shop')}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_shopify_install_no_shop_domain(self):
        shop_domain = '123'
        response_actual = self.desktop_client.get("/platforms/shopify/shops/install", query_string={'shop': '123'})
        response_expected = {"error": 'Shop %s not registered with Opinew.' % shop_domain}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_shopify_install_incorrect_shop_name(self):
        shop_domain = '123456789123456789'
        response_actual = self.desktop_client.get("/platforms/shopify/shops/install", query_string={'shop': shop_domain})
        response_expected = {"error": 'Shop %s not registered with Opinew.' % shop_domain}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_shopify_install_redirect(self):
        response_actual = self.desktop_client.get("/platforms/shopify/shops/install", query_string={'shop': 'opinew.myshopify.com'})
        location_expected = 'https://opinew.myshopify.com/admin/oauth/authorize?client_id=7260cb38253b9adc4af0c90eb622f4ce&scope=read_products,read_orders,read_fulfillments&redirect_uri=http://localhost:5000/platforms/shopify/shops/create&state=opinew'
        self.assertEquals(response_actual.status_code, httplib.FOUND)
        self.assertEquals(location_expected, response_actual.location)

    def test_oauth_callback_no_state(self):
        response_actual = self.desktop_client.get("/platforms/shopify/shops/create")
        response_expected = {u'error': ExceptionMessages.MISSING_PARAM.format(param='state')}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_no_hmac(self):
        response_actual = self.desktop_client.get("/platforms/shopify/shops/create",
                                                  query_string={'state': 'opinew-testing'})
        response_expected = {u'error': ExceptionMessages.MISSING_PARAM.format(param='hmac')}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_no_shop(self):
        response_actual = self.desktop_client.get("/platforms/shopify/shops/create",
                                                  query_string={'state': 'opinew-testing',
                                                                'hmac': 'fdsa'})
        response_expected = {u'error': ExceptionMessages.MISSING_PARAM.format(param='shop')}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_no_code(self):
        response_actual = self.desktop_client.get("/platforms/shopify/shops/create",
                                                  query_string={'state': 'opinew-testing',
                                                                'hmac': 'fdsa',
                                                                'shop': testing_constants.NEW_SHOP_DOMAIN})
        response_expected = {u'error': ExceptionMessages.MISSING_PARAM.format(param='code')}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_wrong_nonce(self):
        response_actual = self.desktop_client.get("/platforms/shopify/shops/create",
                                                  query_string={'state': 'WRONG_NONCE',
                                                                'hmac': 'fdsa',
                                                                'shop': testing_constants.NEW_SHOP_DOMAIN,
                                                                'code': 'abc'})
        response_expected = {u'error': u'Incorrect nonce.'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_no_signature(self):
        response_actual = self.desktop_client.get("/platforms/shopify/shops/create",
                                                  query_string={'state': 'opinewTesting',
                                                                'hmac': 'fdsa',
                                                                'shop': testing_constants.NEW_SHOP_DOMAIN,
                                                                'code': 'abc'})
        response_expected = {u'error': 'Invalid hmac.'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_oauth_callback_hmac_wrong(self):
        response_actual = self.desktop_client.get("/platforms/shopify/shops/create",
                                                  query_string={'state': 'opinewTesting',
                                                                'hmac': 'fdsa',
                                                                'shop': testing_constants.NEW_SHOP_DOMAIN,
                                                                'code': 'abc',
                                                                'signature': 'abc'})
        response_expected = {u'error': u'Invalid hmac.'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_get_index_shop_owner(self):
        self.login(self.shop_owner_user.email, self.shop_owner_password)
        response_actual = self.desktop_client.get(url_for('client.index'))
        location_expected = url_for('client.shop_dashboard')
        self.locationExpected(location_expected, response_actual)
        self.logout()


class TestShopOwnerTrialIncentives(TestFlaskApplication):
    """
    Does the shop owner see a message to enter card details if they are on their trial?
    Do they see how many days are left to do that?
    """
    pass


class TestShopOwnerCardEntry(TestFlaskApplication):
    """
    Can shop owners enter their bank details successfully?
    """
    pass


class TestReviewerReviewPost(TestFlaskApplication):
    """
    Can a user post a review? Unlogged? Logged in? Legacy?
    How about a Picture? Video? Gif? Just stars?
    Can we see the posted review on the plugin?
    """

    def test_render_add_review_no_product(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.desktop_client.get(url_for('client.add_review'))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Select product' in response_actual.data)
        self.logout()

    def test_render_add_review_to_product(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.desktop_client.get(url_for('client.add_review'), query_string={"product_id": 3})
        self.assertEquals(response_actual.status_code, httplib.OK)
        self.logout()

    @freeze_time(testing_constants.ORDER_NOW)
    def test_plugin_get_by_platform_id_not_logged_in(self):
        response_actual = self.desktop_client.get(url_for('client.get_plugin'), query_string=dict(
            shop_id=2, platform_product_id=1, get_by='platform_id'
        ))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h4>See all Ear rings reviews on Opinew</h4>' in response_actual.data)
        self.assertTrue('Perfect unusual accessory for a normal day' in response_actual.data)
        self.assertTrue('Write a review' in response_actual.data)
        self.assertTrue('modal-review' in response_actual.data)

    @freeze_time(testing_constants.ORDER_NOW)
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

    @freeze_time(testing_constants.ORDER_NOW)
    def test_plugin_get_by_url_not_logged_in(self):
        response_actual = self.desktop_client.get(url_for('client.get_plugin'), query_string=dict(
            shop_id=2, product_url='opinew_shop.local:5001/product/1', get_by='url'
        ))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h4>See all Ear rings reviews on Opinew</h4>' in response_actual.data)
        self.assertTrue('Perfect unusual accessory for a normal day' in response_actual.data)
        self.assertTrue('Write a review' in response_actual.data)
        self.assertTrue('modal-review' in response_actual.data)

    @freeze_time(testing_constants.ORDER_NOW)
    def test_plugin_get_by_url_regex_not_logged_in(self):
        response_actual = self.desktop_client.get(url_for('client.get_plugin'), query_string=dict(
            shop_id=2, product_url='opinew_shop.local:5001/something_else/product/1', get_by='url'
        ))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h4>See all Ear rings reviews on Opinew</h4>' in response_actual.data)
        self.assertTrue('Perfect unusual accessory for a normal day' in response_actual.data)
        self.assertTrue('Write a review' in response_actual.data)
        self.assertTrue('modal-review' in response_actual.data)

    @freeze_time(testing_constants.ORDER_NOW)
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


class TestShopifyAPINotifications(TestFlaskApplication):
    """
    Do we get notified on order creation?
    Do we get notified on order fulfilment?
    Do we set up a schedule to send emails?
    """

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
                          name=testing_constants.NEW_PRODUCT_NAME)
        shop = Shop.query.filter_by(id=testing_constants.SHOPIFY_SHOP_ID).first()
        if not shop:
            shop = Shop(domain=testing_constants.SHOPIFY_SHOP_DOMAIN)
            db.session.add(shop)
        product.shop = shop
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
                                          shop=shop).first()
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
            'browser_ip': testing_constants.NEW_ORDER_BROWSER_IP,
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
        self.assertEquals(order.browser_ip, testing_constants.NEW_ORDER_BROWSER_IP)
        self.assertIn(product, order.products)
        db.session.delete(order)
        db.session.delete(product)
        db.session.commit()

    def test_shopify_create_order_already_exists(self):
        order = Order(platform_order_id=testing_constants.NEW_ORDER_PLATFORM_ID)
        db.session.add(order)
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
        self.assertEquals(response_actual.status_code, 401)
        self.assertTrue('Order already exists' in response_actual.data)
        order = Order.query.filter_by(platform_order_id=testing_constants.NEW_ORDER_PLATFORM_ID).first()
        db.session.delete(order)
        db.session.commit()

    @freeze_time(testing_constants.ORDER_NOW)
    def test_shopify_fulfill_order(self):
        product = Product(name=testing_constants.NEW_PRODUCT_NAME)
        order = Order(platform_order_id=testing_constants.NEW_ORDER_PLATFORM_ID,
                      shop_id=testing_constants.SHOPIFY_SHOP_ID, user=self.reviewer_user)
        order.products.append(product)
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


class TestReviewerReviewIncentives(TestFlaskApplication):
    """
    Do users receive emails for reviews?
    Are they spam?
    Do they open them?
    Do they click on the button to review?
    Do they review?
    Do we monitor that?
    """
    pass


class TestShopOwnerPerceivedValueIncentives(TestFlaskApplication):
    """
    Can shop owners see how many reviews are posted because of Opinew on their dashboard?
    Does the plugin go dark after day 30?
    """
    pass


class TestShopOwnerEmailReminders(TestFlaskApplication):
    """
    Do shop owners receive emails for signing up to pay?
    Do we tell them the benefit of Opinew in reviews received?
    On 7, 14, 21, 27 and 30, 31, 35 and 40?
    Are they opened?
    Do we monitor that?
    """
    pass


class TestShopOwnerFailureToPay(TestFlaskApplication):
    """
    Does the plugin go dark after day 30?
    """

    @freeze_time(testing_constants.ORDER_NOW)
    def test_plugin_404(self):
        response_actual = self.desktop_client.get(url_for('client.get_plugin'))
        self.assertEquals(response_actual.status_code, httplib.NOT_FOUND)
        self.assertEquals('', response_actual.data)


class TestShopOwnerCancels(TestFlaskApplication):
    """
    Do we cancel the account properly?
    On stripe?
    On shopify?
    Do we log for how long shop has used it?
    """

    @expect_mail
    def test_shopify_uninstall_app(self):
        shop = Shop.query.filter_by(id=testing_constants.SHOPIFY_SHOP_ID).first()
        shop.owner = self.shop_owner_user
        product = Product(platform_product_id=testing_constants.NEW_PRODUCT_PLATFORM_ID,
                          name=testing_constants.NEW_PRODUCT_NAME,
                          shop_id=testing_constants.SHOPIFY_SHOP_ID)
        order = Order(user_id=1, shop_id=testing_constants.SHOPIFY_SHOP_ID)
        order.products.append(product)
        db.session.add(order)
        db.session.commit()
        order.ship()
        order.set_notifications()
        # emails are sent automatically anyway, just check it happened
        self.assertEquals(len(self.outbox), 1)
        data = json.dumps({})
        sha256 = base64.b64encode(hmac.new(Config.SHOPIFY_APP_SECRET, msg=data, digestmod=hashlib.sha256).digest())
        response_actual = self.desktop_client.post(url_for('api.platform_shopify_app_uninstalled'),
                                                   data=data,
                                                   headers={
                                                       'X-Shopify-Hmac-SHA256': sha256,
                                                       'X-Shopify-Shop-Domain': testing_constants.SHOPIFY_SHOP_DOMAIN})
        self.assertEquals(response_actual.status_code, 200)
        shop = Shop.query.filter_by(id=testing_constants.SHOPIFY_SHOP_ID).first()
        shop_customer = shop.owner.customer[0]
        self.assertFalse(shop_customer.active)
        self.assertEqual(len(shop_customer.subscription), 0)

        # make sure tasks are revoked
        db.session.delete(order)
        db.session.delete(product)
        db.session.commit()

    def test_cancel_stripe(self):
        shop = Shop.query.filter_by(id=testing_constants.SHOPIFY_SHOP_ID).first()
        shop.owner = self.shop_owner_user
        shop.owner.customer.subscription.cancel()
        # self.assertNot
        # self.assertEquals(response_actual.status_code, 200)
        shop = Shop.query.filter_by(id=testing_constants.SHOPIFY_SHOP_ID).first()
        shop_customer = shop.owner.customer[0]
        self.assertFalse(shop_customer.active)
        self.assertIsNone(shop_customer.subscription[0])


class TestShopOwnerIncentivesToStay(TestFlaskApplication):
    """
    Do we send weekly summary of reviews received after payment?
    """
    pass


class TestEmailAdminsOnFailure(TestFlaskApplication):
    """
    Do admins get notified on any failures via email?
    """
    pass


class TestMonitorScalabilityMetrics(TestFlaskApplication):
    """
    Do we monitor our response times?
    How fast are we?
    Do we monitor our CPU, RAM usage, network bandwith and disk space available?
    Do we monitor how many users visit the plugin?
    """
    pass


