import json
from unittest import TestCase
from webapp import create_app, db
from freezegun import freeze_time


class TestAPI(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app('test')
        cls.client = cls.app.test_client()
        cls.app.app_context().push()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()


class TestInstall(TestAPI):
    def test_authentication_no_shop_name(self):
        response_actual = self.client.get("/install", data={})
        response_expected = {"error": "incorrect shop name"}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 400)

    def test_authentication_incorrect_shop_name(self):
        response_actual = self.client.get("/install", data={'shop': 'blablabla'})
        response_expected = {"error": "incorrect shop name"}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 400)

    @freeze_time("2012-04-26")
    def test_authentication_nonce(self):
        response_actual = self.client.get("/install", query_string={'shop': 'shop.myshopify.com'})
        location_expected = 'https://shop.myshopify.com/admin/oauth/authorize?client_id=7260cb38253b9adc4af0c90eb622f4ce&scope=read_products,read_orders,read_fulfillments&redirect_uri=http://162.13.140.76/oauth/callback/1&state=56086732800.0'
        redirect_location = response_actual.headers.get('Location')
        self.assertEquals(redirect_location, location_expected)
        self.assertEquals(response_actual.status_code, 302)
