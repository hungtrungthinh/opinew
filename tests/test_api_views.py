import json
from unittest import TestCase
from webapp import create_app, db
from webapp.models import Product, Review


class TestAPI(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app('test')
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            db.create_all()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()


class TestNonShopTiedAPI(TestAPI):
    def setUp(self):
        product = Product(label='skirt')
        review = Review(body='hello world')
        product.reviews.append(review)
        with self.app.app_context():
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
                    'tags': []
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
            'tags': []
        }
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 200)

    def tearDown(self):
        with self.app.app_context():
            Product.query.delete()
            Review.query.delete()
            db.session.commit()
