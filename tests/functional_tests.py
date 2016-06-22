# -*- coding: utf-8 -*-
import json
from flask import url_for
from tests import testing_constants
from webapp.exceptions import ExceptionMessages
from tests.framework import TestFlaskApplication


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
        response_actual = self.desktop_client.get("/platforms/shopify/shops/install", query_string={'shop': '123'})
        response_expected = {"error": 'Invalid shop domain.'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_shopify_install_incorrect_shop_name(self):
        response_actual = self.desktop_client.get("/platforms/shopify/shops/install", query_string={'ref': 'shopify',
                                                                                                    'shop': '123456789123456789'})
        response_expected = {"error": 'Invalid shop domain.'}
        self.assertEquals(response_expected, json.loads(response_actual.data))

    def test_shopify_install_redirect(self):
        response_actual = self.desktop_client.get("/platforms/shopify/shops/install", query_string={'ref': 'shopify',
                                                                                                    'shop': testing_constants.NEW_SHOP_DOMAIN})
        location_expected = 'https://opinewTesting.myshopify.com/admin/oauth/authorize?client_id=7260cb38253b9adc4af0c90eb622f4ce&scope=read_products,read_orders,read_fulfillments&redirect_uri=http://localhost:5000/platforms/shopify/shops/create&state=opinewTesting'
        self.assertEquals(response_actual.status_code, 302)
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
        response_expected = {u'error': 'signature'}
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
    pass


class TestShopifyAPINotifications(TestFlaskApplication):
    """
    Do we get notified on order creation?
    Do we get notified on order fulfilment?
    Do we set up a schedule to send emails?
    """
    pass


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
    pass


class TestShopOwnerCancels(TestFlaskApplication):
    """
    Do we cancel the account properly?
    On stripe?
    On shopify?
    Do we log for how long shop has used it?
    """
    pass


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


