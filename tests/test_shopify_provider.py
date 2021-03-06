import requests
from flask import url_for
from webapp.models import User
from config import Constants
from webapp import db
from webapp.models import Shop
from tests import testing_constants
from tests.framework import TestFlaskApplication,expect_mail


class TestShopifyShopCreation(TestFlaskApplication):
    # TODO: This test is problematic because of the way tasks are immediatly executed by celery
    # and the way that sqlalchemy's sessions work. See tried attempts in async.tasks.create_customer_account
    # @expect_mail
    # def test_oauth_callback_success(self):
    #     response_actual = self.desktop_client.get("/oauth/callback", query_string={'state': 'opinewTesting',
    #                                                                                'hmac': 'ffbcf1eec0c9740283f750f28a27a2413afcb4158954ec6b1abe63693c6cf15d',
    #                                                                                'shop': testing_constants.NEW_SHOP_DOMAIN,
    #                                                                                'code': 'abc',
    #                                                                                'signature': 'abc'})
    #     location_expected = url_for('client.shop_dashboard', first=1)
    #     self.assertEquals(response_actual.status_code, 302)
    #     self.assertEquals(location_expected, response_actual.location)
    #
    #     new_user = User.query.filter_by(email=testing_constants.NEW_USER_EMAIL).first()
    #     new_shop = Shop.query.filter_by(name=testing_constants.NEW_SHOP_NAME).first()
    #
    #     self.assertTrue(new_user is not None)
    #     self.assertTrue(new_shop is not None)
    #     self.assertEquals(new_user.name, testing_constants.NEW_USER_NAME)
    #     self.assertEquals(new_user.roles[0], Constants.SHOP_OWNER_ROLE)
    #     self.assertEquals(new_shop.owner, new_user)
    #
    #     requests.get(Constants.VIRTUAL_SERVER + "/vshopify/clean_webhooks")
    #     db.session.delete(new_user)
    #     db.session.delete(new_shop)
    #     db.session.commit()

    def test_shopify_install_shop_exists_and_token(self):
        shop = Shop.query.filter_by(name='Opinew shop').first()
        old_shop_domain = shop.domain
        shop.domain = testing_constants.NEW_SHOP_DOMAIN
        shop.access_token = 'Hellotoken'
        for i in range(0, Constants.EXPECTED_WEBHOOKS):
            requests.post(Constants.VIRTUAL_SERVER + "/vshopify/admin/webhooks.json", json={})
        db.session.add(shop)
        db.session.commit()
        response_actual = self.desktop_client.get("/platforms/shopify/shops/install", query_string={'shop': shop.domain})
        location_expected = url_for('client.shop_dashboard_id', shop_id=shop.id)
        self.assertEquals(response_actual.status_code, 302)
        self.assertEquals(location_expected, response_actual.location)
        shop.access_token = None
        requests.get(Constants.VIRTUAL_SERVER + "/vshopify/clean_webhooks")
        shop.domain = old_shop_domain
        db.session.add(shop)
        db.session.commit()

    def test_create_shopify_shop(self):
        from async import tasks
        from providers.platforms import ShopifyAPI

        shop = Shop.query.filter_by(id=3).first()
        self.assertEquals(len(shop.products), 0)
        self.assertEquals(len(shop.orders), 0)
        shopify_api = ShopifyAPI(shop=shop)
        tasks.create_shopify_shop(shop_id=shop.id)
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
        requests.get(Constants.VIRTUAL_SERVER + "/vshopify/clean_webhooks")
        count = shopify_api.check_webhooks_count()
        self.assertEquals(count, 0)
