import requests
import hmac
import hashlib
from flask import request, jsonify
from webapp.exceptions import ApiException, ParamException


class API(object):
    def __init__(self, client_id, client_secret, shop_domain):
        self.client_id = client_id
        self.client_secret = client_secret
        self.shop_domain = shop_domain
        if not len(shop_domain) > 14:
            raise ParamException('invalid shop domain', 400)
        self.shop_name = shop_domain[:-14]

        self.access_token = None

    def initialize_api(self, nonce_request, hmac_request, code):
        self.verify_nonce(nonce_request)
        self.verify_hmac(hmac_request)
        self.verify_shop_name()
        self.get_access_token(code)

    def verify_nonce(self, nonce_request):
        if not nonce_request:
            raise ParamException('no nonce', 400)
        if not nonce_request == self.shop_name:
            raise ParamException('incorrect nonce', 400)

    def verify_hmac(self, hmac_request):
        if not hmac_request:
            raise ParamException('incorrect shop name', 400)
        req = dict(request.args)
        del req['signature']
        del req['hmac']
        unsorted = []
        for key, value in req.iteritems():
            key = key.replace('%', '%25').replace('&', '%26').replace('=', '%3D')
            value = value[0].replace('%', '%25').replace('&', '%26')
            pair = '%s=%s' % (key, value)
            unsorted.append(pair)
        hmac_message = '&'.join(sorted(unsorted))
        dig = hmac.new(self.client_secret, msg=hmac_message, digestmod=hashlib.sha256).hexdigest()
        if not hmac_request == dig:
            raise ParamException('hmac unverified', 400)

    def verify_shop_name(self):
        if not self.shop_domain[-14:] == '.myshopify.com':
            raise ParamException('incorrect shop name', 400)

    def get_access_token(self, code):
        r = requests.post('https://{shop}.myshopify.com/admin/oauth/access_token'.format(
            shop=self.shop_domain[:-14]),
            data={'client_id': self.client_id,
                  'client_secret': self.client_secret,
                  'code': code})

        if not r.status_code == 200:
            raise ApiException(r.text, r.status_code)
        access_token = r.json().get('access_token')
        self.access_token = access_token

    def create_webhook(self, topic, address):
        r = requests.post("https://%s/admin/webhooks.json" % self.shop_domain,
                          headers={'X-Shopify-Access-Token': self.access_token},
                          json={
                              "webhook": {
                                  "topic": topic,
                                  "address": address,
                                  "format": "json"
                              }
                          })

    def get_shop(self):
        r = requests.get("https://%s/admin/shop.json" % self.shop_domain,
                         headers={'X-Shopify-Access-Token': self.access_token})
        if not r.status_code == 200:
            raise ApiException(r.text, r.status_code)
        response = r.json()
        return response.get('shop', {})

    def get_products(self):
        r = requests.get("https://%s/admin/products.json" % self.shop_domain,
                         headers={'X-Shopify-Access-Token': self.access_token})
        if not r.status_code == 200:
            raise ApiException(r.text, r.status_code)
        response = r.json()
        return response.get('products', [])
