from unittest import TestCase
from webapp.api.views import shop_domain_parse
from webapp.exceptions import ExceptionMessages
import httplib


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
        from flask.ext.restless import ProcessingException
        data = {
            'domain': 'ftp://hello_world.com'
        }
        with self.assertRaises(ProcessingException) as e:
            shop_domain_parse(data)
        the_exception = e.exception
        self.assertEqual(the_exception.description, ExceptionMessages.DOMAIN_NEEDED)
        self.assertEqual(the_exception.code, httplib.BAD_REQUEST)
