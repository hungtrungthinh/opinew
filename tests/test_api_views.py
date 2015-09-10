import os
import json
from unittest import TestCase
from flask import url_for
from flask.ext.uploads import TestingFileStorage
from webapp import create_app, db
from webapp.common import post_with_auth, patch_with_auth
from webapp.models import User, Product, Review, Shop, ShopProduct, Order
from config import Config


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


class TestNonShopTiedAPI(TestAPI):
    @classmethod
    def setUpClass(cls):
        super(TestNonShopTiedAPI, cls).setUpClass()
        product = Product(label='skirt')
        review = Review(body='hello world')
        product.reviews.append(review)
        db.session.add(product)
        db.session.commit()

    def test_search_incorrect_params(self):
        response_actual = self.client.get("/api/products/search")
        response_expected = {'error': 'q parameter is required'}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 400)

    def test_search_zero_results(self):
        response_actual = self.client.get("/api/products/search", query_string={'q': 'nope'})
        response_expected = {'products': []}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 200)

    def test_search_one_result(self):
        response_actual = self.client.get("/api/products/search", query_string={'q': 'skirt'})
        response_expected = {'products': [{'id': 1, 'label': 'skirt'}]}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 200)

    def test_reviews_nonexistent_product(self):
        response_actual = self.client.get("/api/products/0/reviews")
        response_expected = {'error': 'Product doesn\'t exist'}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 404)

    def test_reviews_existing_product(self):
        response_actual = self.client.get("/api/products/1/reviews")
        response_expected = {
            'id': 1,
            'label': 'skirt',
            'tags': [],
            'reviews': [
                {
                    'id': 1,
                    'body': 'hello world',
                    'photo_url': None,
                    'tags': [],
                    'approved_by_shop': False,
                    'approval_pending': True
                }
            ]
        }
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 200)

    def test_product_nonexistent(self):
        response_actual = self.client.get("/api/products/0")
        response_expected = {'error': 'Product doesn\'t exist'}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 404)

    def test_product_success(self):
        response_actual = self.client.get("/api/products/1")
        response_expected = {
            'id': 1,
            'label': 'skirt',
            'tags': []
        }
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 200)

    def test_review_nonexistent(self):
        response_actual = self.client.get("/api/reviews/0")
        response_expected = {'error': 'Review doesn\'t exist'}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 404)

    def test_review_success(self):
        response_actual = self.client.get("/api/reviews/1")
        response_expected = {
            'id': 1,
            'body': 'hello world',
            'photo_url': None,
            'tags': [],
            'approved_by_shop': False,
            'approval_pending': True
        }
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 200)


class TestShopTiedAPI(TestAPI):
    @classmethod
    def setUpClass(cls):
        super(TestShopTiedAPI, cls).setUpClass()
        shop = Shop(label='My shop')
        product = Product(label='skirt')
        review = Review(body='hello world')
        product.reviews.append(review)
        shop_product = ShopProduct(shop=shop, product=product)
        db.session.add(shop_product)
        db.session.commit()

    def test_search_incorrect_params(self):
        response_actual = self.client.get("/api/shops/1/products/search")
        response_expected = {'error': 'q parameter is required'}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 400)

    def test_shop_product_search_shop_not_registered(self):
        response_actual = self.client.get("/api/shops/26/products/search", query_string={'q': 'skirt'})
        response_expected = {'error': 'Shop 26 not registered with Opinew.'}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 400)

    def test_shop_product_search_zero_results(self):
        response_actual = self.client.get("/api/shops/1/products/search", query_string={'q': 'nope'})
        response_expected = {'products': []}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 200)

    def test_shop_product_search_success(self):
        response_actual = self.client.get("/api/shops/1/products/search", query_string={'q': 'skirt'})
        response_expected = {'products': [{'id': 1, 'label': 'skirt'}]}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 200)

    def test_shop_prodcut_incorrect_shop_not_registered(self):
        response_actual = self.client.get("/api/shops/42/products/0/reviews")
        response_expected = {'error': 'Shop 42 not registered with Opinew.'}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 400)

    def test_shop_product_search_shop_product_not_exist(self):
        response_actual = self.client.get("/api/shops/1/products/42/reviews")
        response_expected = {'error': 'Product doesn\'t exist'}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 404)

    def test_shop_reviews_existing_product(self):
        response_actual = self.client.get("/api/shops/1/products/1/reviews")
        response_expected = {
            'id': 1,
            'label': 'skirt',
            'tags': [],
            'reviews': [
                {
                    'id': 1,
                    'body': 'hello world',
                    'approved_by_shop': False,
                    'approval_pending': True,
                    'photo_url': None,
                    'tags': []
                }
            ]
        }
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 200)

    def test_shop_reviews_existing_product_approved(self):
        review = Review.query.filter_by(id=1).first()
        review.approve()
        db.session.add(review)
        db.session.commit()
        response_actual = self.client.get("/api/shops/1/products/1/reviews")
        response_expected = {
            'id': 1,
            'label': 'skirt',
            'tags': [],
            'reviews': [
                {
                    'id': 1,
                    'body': 'hello world',
                    'approved_by_shop': True,
                    'approval_pending': False,
                    'photo_url': None,
                    'tags': []
                }
            ]
        }
        review.approved_by_shop = False
        review.approval_pending = True
        db.session.add(review)
        db.session.commit()
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 200)

    def test_shop_reviews_existing_product_disapproved(self):
        review = Review.query.filter_by(id=1).first()
        review.dispprove()
        db.session.add(review)
        db.session.commit()
        response_actual = self.client.get("/api/shops/1/products/1/reviews")
        response_expected = {
            'id': 1,
            'label': 'skirt',
            'tags': [],
            'reviews': [
                {
                    'id': 1,
                    'body': 'hello world',
                    'approved_by_shop': False,
                    'approval_pending': False,
                    'photo_url': None,
                    'tags': []
                }
            ]
        }
        review.approved_by_shop = False
        review.approval_pending = True
        db.session.add(review)
        db.session.commit()
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 200)


class TestAuthenticateAPI(TestAPI):
    @classmethod
    def setUpClass(cls):
        cls.USER_EMAIL = 'test@example.com'
        cls.USER_PWD = 'testing'

        super(TestAuthenticateAPI, cls).setUpClass()
        user = User(email=cls.USER_EMAIL, password=cls.USER_PWD)
        db.session.add(user)
        db.session.commit()

    def test_authentication_no_email(self):
        response_actual = self.client.post("/api/authenticate", data={'password': self.USER_PWD})
        response_expected = {'error': 'email parameter is required'}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 400)

    def test_authentication_no_password(self):
        response_actual = self.client.post("/api/authenticate", data={'email': self.USER_EMAIL})
        response_expected = {'error': 'password parameter is required'}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 400)

    def test_non_existing_user_authentication(self):
        response_actual = self.client.post("/api/authenticate", data={'email': 'nope',
                                                                      'password': self.USER_PWD})
        response_expected = {'error': 'User with email nope does not exist.'}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 400)

    def test_user_authentication_wrong_password(self):
        response_actual = self.client.post("/api/authenticate", data={'email': self.USER_EMAIL,
                                                                      'password': 'incorrect'})
        response_expected = {'error': 'Wrong password.'}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 400)

    def test_correct_authentication(self):
        response_actual = self.client.post("/api/authenticate", data={'email': self.USER_EMAIL,
                                                                      'password': self.USER_PWD})
        response_expected = {}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 200)


class TestAuthenticationRequiredAPI(TestAPI):
    @classmethod
    def setUpClass(cls):
        super(TestAuthenticationRequiredAPI, cls).setUpClass()

        cls.USER_SHOP_OWNER_EMAIL = 'shop_owner@example.com'
        cls.USER_SHOP_OWNER_PWD = 'shop_testing'
        cls.USER_EMAIL = 'test@example.com'
        cls.USER_PWD = 'testing'
        cls.SHOP_LABEL = 'My shop'
        cls.PRODUCT_LABEL = 'skirt'

        shop_owner = User(email=cls.USER_SHOP_OWNER_EMAIL, password=cls.USER_SHOP_OWNER_PWD)
        user = User(email=cls.USER_EMAIL, password=cls.USER_PWD)
        shop = Shop(label=cls.SHOP_LABEL)
        shop.owner = shop_owner
        product = Product(label=cls.PRODUCT_LABEL)
        shop_product = ShopProduct(shop=shop, product=product)
        order = Order(user=user, shop=shop, product=product)
        review = Review(body='first')
        order.review = review

        db.session.add(shop_product)
        db.session.add(order)
        db.session.add(user)
        db.session.commit()

    def test_add_shop_product_review_no_content(self):
        response_actual = post_with_auth(self.client,
                                         url_for('api.add_shop_product_review', shop_id=1, product_id=1),
                                         username=self.USER_EMAIL,
                                         password=self.USER_PWD)
        response_expected = {'error': 'At least one of body, photo or tags need to be provided.'}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 400)

    def test_add_shop_product_review_body(self):
        review_body = 'Hello world'

        response_actual = post_with_auth(self.client,
                                         url_for('api.add_shop_product_review', shop_id=1, product_id=1),
                                         username=self.USER_EMAIL,
                                         password=self.USER_PWD,
                                         data={'body': review_body})
        response_expected = {}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 201)
        review = Review.get_last()
        self.assertEquals(review.body, review_body)

    def test_add_shop_product_review_photo(self):
        review_photo_name = 'hello_world.png'

        response_actual = post_with_auth(self.client,
                                         url_for('api.add_shop_product_review', shop_id=1, product_id=1),
                                         username=self.USER_EMAIL,
                                         password=self.USER_PWD,
                                         data={'photo': TestingFileStorage(filename=review_photo_name)})
        response_expected = {}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 201)
        review = Review.get_last()
        self.assertEquals(review.photo_url, review_photo_name)
        fpath = os.path.join(Config.UPLOADED_REVIEWPHOTOS_DEST, review_photo_name)
        try:
            os.remove(fpath)
        except OSError:
            pass

    def test_approve_shop_product_review(self):
        response_actual = patch_with_auth(self.client,
                                         url_for('api.approve_shop_product_review', shop_id=1, review_id=1),
                                         username=self.USER_SHOP_OWNER_EMAIL,
                                         password=self.USER_SHOP_OWNER_PWD,
                                         data={'action': 'approve'})
        response_expected = ''
        self.assertEquals(response_actual.data, response_expected)
        self.assertEquals(response_actual.status_code, 204)
