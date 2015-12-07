import requests
from flask import url_for
from webapp.models import User
from config import Constants
from webapp import db
from webapp.models import Shop
from tests import testing_constants
from tests.framework import TestFlaskApplication

class TestShopifyShopCreation(TestFlaskApplication):
    @classmethod
    def setUpClass(cls):
        super(TestShopifyShopCreation, cls).setUpClass()
        # Start a virtual shopify API on port 5678
        import threading
        from flask import Flask, request
        from webapp.vshopify import vshopify
        vshopify_app = Flask(__name__)
        vshopify_app.register_blueprint(vshopify, url_prefix='/vshopify')

        def shutdown_server():
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                raise RuntimeError('Not running with the Werkzeug Server')
            func()

        @vshopify_app.route('/shutdown', methods=['POST'])
        def shutdown():
            shutdown_server()
            return 'Server shutting down...'

        cls.t = threading.Thread(target=vshopify_app.run, kwargs=dict(port=5678, use_reloader=False, debug=True))
        cls.t.start()

    def test_oauth_callback_success(self):
        response_actual = self.desktop_client.get("/oauth/callback", query_string={'state': 'opinew-testing',
                                                                                   'hmac': '4989858235c2ceded8d751658b9a8d7af995343950bcf65bee49ea48fb20380e',
                                                                                   'shop': testing_constants.NEW_SHOP_DOMAIN,
                                                                                   'code': 'abc',
                                                                                   'signature': 'abc'})
        location_expected = url_for('client.shop_dashboard', first=1)
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

    def test_shopify_install_shop_exists_and_token(self):
        shop = Shop.query.filter_by(name='Opinew shop').first()
        old_shop_domain = shop.domain
        shop.domain = testing_constants.NEW_SHOP_DOMAIN
        shop.access_token = 'Hellotoken'
        db.session.add(shop)
        db.session.commit()
        response_actual = self.desktop_client.get("/install", query_string={'ref': 'shopify',
                                                                            'shop': shop.domain})
        location_expected = url_for('client.shop_dashboard')
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)
        shop.access_token = None
        shop.domain = old_shop_domain
        db.session.add(shop)
        db.session.commit()

    def test_create_shopify_shop(self):
        from async import tasks
        from providers.shopify_api import API

        shop = Shop.query.filter_by(id=3).first()
        self.assertEquals(len(shop.products), 0)
        self.assertEquals(len(shop.orders), 0)
        shopify_api = API(shop_domain=shop.domain)
        tasks.create_shopify_shop(shopify_api=shopify_api, shop_id=shop.id)
        shop = Shop.query.filter_by(id=3).first()
        # check webhooks count
        count = shopify_api.check_webhooks_count()
        self.assertEquals(count, 6)
        self.assertEquals(len(shop.products), 1)
        self.assertEquals(shop.products[0].platform_product_id, testing_constants.NEW_PRODUCT_PLATFORM_ID)
        self.assertEquals(shop.products[0].name, testing_constants.NEW_PRODUCT_NAME)
        self.assertEquals(len(shop.orders), 1)
        self.assertEquals(shop.orders[0].platform_order_id, testing_constants.NEW_ORDER_PLATFORM_ID)
        self.assertEquals(len(shop.orders[0].products), 1)
        self.assertEquals(shop.orders[0].products[0].platform_product_id, testing_constants.NEW_PRODUCT_PLATFORM_ID)
        # clean webhooks
        requests.get("http://localhost:5678/vshopify/clean_webhooks")
        count = shopify_api.check_webhooks_count()
        self.assertEquals(count, 0)

    @classmethod
    def tearDownClass(cls):
        # Shutdown the server and join the thread
        super(TestShopifyShopCreation, cls).tearDownClass()
        requests.post('http://localhost:5678/shutdown')
        cls.t.join()
