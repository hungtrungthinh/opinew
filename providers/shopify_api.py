import requests
import hmac
import hashlib
from flask import request, current_app
from webapp.exceptions import ApiException, ParamException
from config import Constants


class API(object):
    def __init__(self, client_id=None, client_secret=None, shop_domain=None, access_token=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.shop_domain = shop_domain
        if not len(shop_domain) > 14:
            raise ParamException('invalid shop domain', 400)
        self.shop_name = shop_domain[:-14]

        self.access_token = access_token

        self.url_prefix = current_app.config.get(
            'SHOPIFY_PREFIX') % 'vshopify' if current_app.testing else 'https://%s' % self.shop_domain

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
        if not 'signature' in req:
            raise ParamException('signature required', 400)
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
        r = requests.post('%s/admin/oauth/access_token' % self.url_prefix,
            data={'client_id': self.client_id,
                  'client_secret': self.client_secret,
                  'code': code})

        if not r.status_code == 200:
            raise ApiException(r.text, r.status_code)
        json_r = r.json()
        access_token = json_r.get('access_token')
        self.access_token = access_token

    def check_webhooks_count(self):
        r = requests.get("%s/admin/webhooks/count.json" % self.url_prefix,
                         headers={'X-Shopify-Access-Token': self.access_token})
        if not r.status_code == 200:
            raise ApiException(r.text, r.status_code)
        response = r.json()
        return response.get('count', 0)

    def check_webhooks(self):
        r = requests.get("%s/admin/webhooks.json" % self.url_prefix,
                         headers={'X-Shopify-Access-Token': self.access_token})
        if not r.status_code == 200:
            raise ApiException(r.text, r.status_code)
        response = r.json()
        return response

    def create_webhook(self, topic, address):
        requests.post("%s/admin/webhooks.json" % self.url_prefix,
                      headers={'X-Shopify-Access-Token': self.access_token},
                      json={
                          "webhook": {
                              "topic": topic,
                              "address": address,
                              "format": "json"
                          }
                      })

    def get_shop(self):
        r = requests.get("%s/admin/shop.json" % self.url_prefix,
                         headers={'X-Shopify-Access-Token': self.access_token})
        if not r.status_code == 200:
            raise ApiException(r.text, r.status_code)
        response = r.json()
        return response.get('shop', {})

    def get_products_count(self):
        r = requests.get("%s/admin/products/count.json" % self.url_prefix,
                         headers={'X-Shopify-Access-Token': self.access_token})
        if not r.status_code == 200:
            raise ApiException(r.text, r.status_code)
        response = r.json()
        return response.get('count', 0)

    def get_products(self, limit=Constants.SHOPIFY_MAX_PRODUCTS_PER_PAGE, page=1):
        r = requests.get("%s/admin/products.json?limit=%s&page=%s" % (self.url_prefix, limit, page),
                         headers={'X-Shopify-Access-Token': self.access_token})
        if not r.status_code == 200:
            raise ApiException(r.text, r.status_code)
        response = r.json()
        return response.get('products', [])

    def get_orders_count(self):
        r = requests.get("%s/admin/orders/count.json?status=any" % self.url_prefix,
                         headers={'X-Shopify-Access-Token': self.access_token})
        if not r.status_code == 200:
            raise ApiException(r.text, r.status_code)
        response = r.json()
        return response.get('count', 0)

    def get_orders(self, limit=Constants.SHOPIFY_MAX_PRODUCTS_PER_PAGE, page=1):
        r = requests.get("%s/admin/orders.json?status=any&limit=%s&page=%s" % (self.url_prefix, limit, page),
                         headers={'X-Shopify-Access-Token': self.access_token})
        if not r.status_code == 200:
            raise ApiException(r.text, r.status_code)
        response = r.json()
        return response.get('orders', [])

import datetime
import pytz
from webapp import models, db, exceptions
from dateutil import parser as date_parser


def create_order(shop, payload):
    platform_order_id = str(payload.get('id', ''))
    existing_order = models.Order.query.filter_by(platform_order_id=platform_order_id).first()
    if existing_order:
        raise exceptions.DbException('Order already exists', status_code=401)
    try:
        created_at_dt = date_parser.parse(payload.get('created_at')).astimezone(pytz.utc).replace(tzinfo=None)
    except:
        created_at_dt = datetime.datetime.utcnow()
    browser_ip = str(payload.get('browser_ip', ''))
    order = models.Order(platform_order_id=platform_order_id, shop=shop, purchase_timestamp=created_at_dt,
                         browser_ip=browser_ip)

    # try to speculatively find a FunnelStream to match for this order - from this browser IP, latest
    funnel_stream = None
    if browser_ip:
        funnel_stream = models.FunnelStream.query.filter_by(plugin_loaded_from_ip=browser_ip).order_by(models.FunnelStream.plugin_load_ts.desc()).first()
        if funnel_stream:
            funnel_stream.order = order
            db.session.add(funnel_stream)

    customer_email = payload.get('customer', {}).get('email')
    customer_name = "%s %s" % (payload.get('customer', {}).get('first_name', ''),  payload.get('customer', {}).get('last_name', ''))
    existing_user = models.User.get_by_email_no_exception(customer_email)
    if existing_user:
        order.user = existing_user
    else:
        user_legacy, _ = models.UserLegacy.get_or_create_by_email(customer_email, name=customer_name)
        order.user_legacy = user_legacy

    line_items = payload.get('line_items', [])
    for line_item in line_items:
        platform_product_id = str(line_item.get('product_id'))
        product = models.Product.query.filter_by(platform_product_id=platform_product_id, shop_id=shop.id).first()
        if product:
            order.products.append(product)
        else:
            variant = models.ProductVariant.query.filter_by(platform_variant_id=str(line_item.get('variant_id'))).first()
            if not variant:
                continue
            order.products.append(variant.product)
        order.products.append(product)

    db.session.add(order)
    db.session.commit()


def fulfill_order(shop, payload):
    platform_order_id = str(payload.get('order_id', ''))

    order = models.Order.query.filter_by(platform_order_id=platform_order_id, shop_id=shop.id).first()
    delivery_tracking_number = payload.get('tracking_number')
    if order:
        created_at = payload.get('created_at')
        st = date_parser.parse(created_at).astimezone(pytz.utc).replace(tzinfo=None)
        if not order.status == Constants.ORDER_STATUS_SHIPPED:
            order.ship(delivery_tracking_number, shipment_timestamp=st)
            order.set_notifications()
