import httplib
from unittest import TestCase
from flask.ext.security import login_user
from webapp import models, db, create_app
from webapp.api.views import shop_domain_parse, verify_request_by_shop_owner, verify_product_url_is_from_shop_domain
from webapp.exceptions import ExceptionMessages
from flask.ext.restless import ProcessingException
from config import Constants

app = create_app('testing')


class TestShopDomainParse(TestCase):
    SCHEMALESS_DOMAIN = 'www.example.com'
    HTTP_DOMAIN = 'http://' + SCHEMALESS_DOMAIN
    HTTPS_DOMAIN = 'https://' + SCHEMALESS_DOMAIN

    def test_schemaless_domain(self):
        data = {
            'domain': self.SCHEMALESS_DOMAIN
        }
        shop_domain_parse(data)
        self.assertEqual(data['domain'], self.HTTP_DOMAIN)

    def test_http_domain(self):
        data = {
            'domain': self.HTTP_DOMAIN
        }
        shop_domain_parse(data)
        self.assertEqual(data['domain'], self.HTTP_DOMAIN)

    def test_https_domain(self):
        data = {
            'domain': self.HTTPS_DOMAIN
        }
        shop_domain_parse(data)
        self.assertEqual(data['domain'], self.HTTPS_DOMAIN)

    def test_no_domain(self):
        data = {}
        shop_domain_parse(data)
        self.assertIsNone(data.get('domain'))

    def test_invalid_schema(self):
        data = {
            'domain': 'ftp://hello_world.com'
        }
        with self.assertRaises(ProcessingException) as e:
            shop_domain_parse(data)
        the_exception = e.exception
        self.assertEqual(the_exception.description, ExceptionMessages.DOMAIN_NEEDED)
        self.assertEqual(the_exception.code, httplib.BAD_REQUEST)


class TestVerifyRequestByShopOwner(TestCase):
    SHOP_ID = None
    SHOP_NOT_OWNED_ID = None
    SHOP_OWNER_USER = None
    SHOP_ID_NOT_EXIST = 798789
    SHOP_PARAM_NOT_INTEGER = 'abracadabra'

    @classmethod
    def setUpClass(cls):
        app.app_context().push()
        db.create_all()
        cls.SHOP_OWNER_USER = models.User()
        shop = models.Shop(owner=cls.SHOP_OWNER_USER)
        shop_not_owned = models.Shop()
        db.session.add(shop)
        db.session.add(shop_not_owned)
        db.session.commit()
        cls.SHOP_ID = shop.id
        cls.SHOP_NOT_OWNED_ID = shop_not_owned.id

    def setUp(self):
        ctx = app.test_request_context('/')
        ctx.push()
        login_user(self.SHOP_OWNER_USER)

    def test_user_is_owner(self):
        data = {
            'shop_id': self.SHOP_ID
        }
        verify_request_by_shop_owner(data)
        self.assertTrue(True)

    def test_no_shop_id_arg(self):
        data = {}
        with self.assertRaises(ProcessingException) as e:
            verify_request_by_shop_owner(data)
        the_exception = e.exception
        self.assertEqual(the_exception.description, ExceptionMessages.MISSING_PARAM.format(param='shop_id'))
        self.assertEqual(the_exception.code, httplib.BAD_REQUEST)

    def test_param_not_integer(self):
        data = {
            'shop_id': self.SHOP_PARAM_NOT_INTEGER
        }
        with self.assertRaises(ProcessingException) as e:
            verify_request_by_shop_owner(data)
        the_exception = e.exception
        self.assertEqual(the_exception.description, ExceptionMessages.PARAM_NOT_INTEGER.format(param='shop_id'))
        self.assertEqual(the_exception.code, httplib.BAD_REQUEST)

    def test_no_shop_with_id(self):
        data = {
            'shop_id': self.SHOP_ID_NOT_EXIST
        }
        with self.assertRaises(ProcessingException) as e:
            verify_request_by_shop_owner(data)
        the_exception = e.exception
        self.assertEqual(the_exception.description, ExceptionMessages.INSTANCE_NOT_EXISTS.format(instance='shop',
                                                                                                 id=self.SHOP_ID_NOT_EXIST))
        self.assertEqual(the_exception.code, httplib.BAD_REQUEST)

    def test_user_is_not_owner(self):
        data = {
            'shop_id': self.SHOP_NOT_OWNED_ID
        }
        with self.assertRaises(ProcessingException) as e:
            verify_request_by_shop_owner(data)
        the_exception = e.exception
        self.assertEqual(the_exception.description, ExceptionMessages.NOT_YOUR_SHOP)
        self.assertEqual(the_exception.code, httplib.UNAUTHORIZED)

    def tearDown(self):
        db.session.remove()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()


class TestVerifyProductUrlIsFromShopDomain(TestCase):
    SHOP_ID = None
    PRODUCT_URL_NO_SCHEMA = 'domain.com/some/product/url'
    PRODUCT_URL_HTTP = 'http://domain.com/some/product/url'
    PRODUCT_URL_HTTPS = 'https://domain.com/some/product/url'
    PRODUCT_URL_NO_SCHEMA_NOT_WITHIN_SHOP_DOMAIN = 'notindomain.bg/some/product/url'
    PRODUCT_URL_HTTPS_NOT_WITHIN_SHOP_DOMAIN = 'https://notindomain.bg/some/product/url'
    PRODUCT_URL_HTTP_NOT_WITHIN_SHOP_DOMAIN = 'http://notindomain.bg/some/product/url'
    SHOP_DOMAIN = 'http://domain.com'

    @classmethod
    def setUpClass(cls):
        app.app_context().push()
        db.create_all()
        shop = models.Shop(domain=cls.SHOP_DOMAIN)
        db.session.add(shop)
        db.session.commit()
        cls.SHOP_ID = shop.id

    def test_url_no_schema(self):
        data = {
            'shop_id': self.SHOP_ID,
            'url': self.PRODUCT_URL_NO_SCHEMA
        }
        verify_product_url_is_from_shop_domain(data)
        self.assertTrue(True)

    def test_url_http_schema(self):
        data = {
            'shop_id': self.SHOP_ID,
            'url': self.PRODUCT_URL_HTTP
        }
        verify_product_url_is_from_shop_domain(data)
        self.assertTrue(True)

    def test_url_https_schema(self):
        data = {
            'shop_id': self.SHOP_ID,
            'url': self.PRODUCT_URL_HTTPS
        }
        verify_product_url_is_from_shop_domain(data)
        self.assertTrue(True)

    def test_url_https_not_within_shop_domain(self):
        data = {
            'shop_id': self.SHOP_ID,
            'url': self.PRODUCT_URL_HTTPS_NOT_WITHIN_SHOP_DOMAIN
        }
        with self.assertRaises(ProcessingException) as e:
            verify_product_url_is_from_shop_domain(data)
        the_exception = e.exception
        self.assertEqual(the_exception.description, ExceptionMessages.PRODUCT_NOT_WITHIN_SHOP_DOMAIN.format(
                shop_domain=self.SHOP_DOMAIN))
        self.assertEqual(the_exception.code, httplib.UNAUTHORIZED)

    def test_url_http_not_within_shop_domain(self):
        data = {
            'shop_id': self.SHOP_ID,
            'url': self.PRODUCT_URL_HTTP_NOT_WITHIN_SHOP_DOMAIN
        }
        with self.assertRaises(ProcessingException) as e:
            verify_product_url_is_from_shop_domain(data)
        the_exception = e.exception
        self.assertEqual(the_exception.description, ExceptionMessages.PRODUCT_NOT_WITHIN_SHOP_DOMAIN.format(
                shop_domain=self.SHOP_DOMAIN))
        self.assertEqual(the_exception.code, httplib.UNAUTHORIZED)

    def test_url_no_schema_not_within_shop_domain(self):
        data = {
            'shop_id': self.SHOP_ID,
            'url': self.PRODUCT_URL_NO_SCHEMA_NOT_WITHIN_SHOP_DOMAIN
        }
        with self.assertRaises(ProcessingException) as e:
            verify_product_url_is_from_shop_domain(data)
        the_exception = e.exception
        self.assertEqual(the_exception.description, ExceptionMessages.PRODUCT_NOT_WITHIN_SHOP_DOMAIN.format(
                shop_domain=self.SHOP_DOMAIN))
        self.assertEqual(the_exception.code, httplib.UNAUTHORIZED)

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()


class TestGetReviewUserName(TestCase):
    USER_NAME = 'Peter Griffin'

    def test_no_user_name(self):
        review = models.Review()
        self.assertEquals(review.user_name, Constants.DEFAULT_ANONYMOUS_USER_NAME)

    def test_user_name_valid(self):
        user = models.User(name=self.USER_NAME)
        review = models.Review.create_for_test(user=user)
        self.assertEquals(review.user_name, self.USER_NAME)

    def test_user_name_from_source(self):
        review = models.Review.create_for_test(source_id=15, source_user_name=self.USER_NAME)
        self.assertEquals(review.user_name, self.USER_NAME)


class TestGetReviewUserImageUrl(TestCase):
    pass
    # TODO
