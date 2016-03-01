import datetime
import hashlib
import hmac
import pytz
import requests
from flask import request, current_app, g
from webapp.exceptions import ApiException, ParamException
from config import Constants
from webapp import models, db, exceptions
from dateutil import parser as date_parser


class ShopifyAPI(object):
    def __init__(self, client_id=None, client_secret=None, shop=None):
        self.client_id = client_id
        self.client_secret = client_secret

        self.shop = shop

        if shop:
            self.shop_domain = shop.domain
            self.shop_name = self.shop_domain[:-14]
            self.access_token = shop.access_token
            if current_app.testing:
                self.url_prefix = current_app.config.get('SHOPIFY_PREFIX') % 'vshopify'
            else:
                self.url_prefix = 'https://%s' % self.shop_domain

    def initialize_api(self, shop_domain, nonce_request, hmac_request, code):
        self.shop_domain = shop_domain
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


class ShopifyOpinewAdapter(object):
    def product_variant(self, shopify_product_variant):
        platform_variant_id = str(shopify_product_variant.get('id', ''))
        existing_product_variant = g.db.ProductVariant.get_by_platform_variant_id(platform_variant_id)
        if existing_product_variant:
            return None
        product_variant = g.db.ProductVariant.create(platform_variant_id=platform_variant_id)
        return product_variant

    def product(self, shopify_product):
        product_name = shopify_product.get('title', '')
        platform_product_id = shopify_product.get('id', '')
        existing_product = g.db.Product.get_by_platform_product_id(platform_product_id)
        if not existing_product:
            product = g.db.Product.create(name=product_name,
                                      platform_product_id=platform_product_id)
        else:
            product = existing_product
        for shopify_product_variant in shopify_product.get('variants', []):
            product_variant = self.product_variant(shopify_product_variant)
            if product_variant:
                product_variant.product = product
        return product

    def order(self, shopify_order):
        platform_order_id = str(shopify_order.get('id', 0))
        purchase_timestamp = datetime.datetime.strptime(shopify_order.get('created_at')[:-6], "%Y-%m-%dT%H:%M:%S")
        user_email = shopify_order.get('email')
        user_first_name = shopify_order.get('customer', {}).get('first_name')
        user_last_name = shopify_order.get('customer', {}).get('last_name')
        user_name = "%s %s" % (user_first_name, user_last_name)

        existing_order = g.db.Order.get_by_platform_order_id(platform_order_id=platform_order_id)
        if existing_order:
            return None

        order = g.db.Order.create(purchase_timestamp=purchase_timestamp,
                                  platform_order_id=platform_order_id)

        existing_user = g.db.User.get_by_email(user_email)
        if existing_user:
            order.user = existing_user
        else:
            user = g.db.User.create_legacy(email=user_email, name=user_name)
            order.user = user

        if shopify_order.get('fulfillment_status'):
            order.status = Constants.ORDER_STATUS_SHIPPED
        if shopify_order.get('cancelled_at'):
            order.status = Constants.ORDER_STATUS_FAILED
        for shopify_product in shopify_order.get('line_items', []):
            platform_product_id = str(shopify_product.get('product_id', ''))
            product = g.db.Product.get_by_platform_product_id(platform_product_id)

            if product:
                order.products.append(product)
            else:
                platform_variant_id = str(shopify_product.get('variant_id', ''))
                variant = g.db.ProductVariant.get_by_platform_variant_id(platform_variant_id)
                if not variant:
                    continue
                order.products.append(variant.product)
        return order

class OpinewShopifyFacade(object):
    def __init__(self, shop=None):
        self.shop = shop
        self.shopify_api = ShopifyAPI(shop=shop)
        self.shop_name = self.get_shop_name()
        self.adapter = ShopifyOpinewAdapter()

    def create_webhooks(self):
        # Create webhooks
        self.shopify_api.create_webhook("products/create",
                                        "%s%s" % (current_app.config.get('OPINEW_API_SERVER'),
                                                  "/api/v1/platform/shopify/products/create"))
        self.shopify_api.create_webhook("products/update",
                                        "%s%s" % (current_app.config.get('OPINEW_API_SERVER'),
                                                  "/api/v1/platform/shopify/products/update"))
        self.shopify_api.create_webhook("products/delete",
                                        "%s%s" % (current_app.config.get('OPINEW_API_SERVER'),
                                                  "/api/v1/platform/shopify/products/delete"))
        self.shopify_api.create_webhook("orders/create",
                                        "%s%s" % (current_app.config.get('OPINEW_API_SERVER'),
                                                  "/api/v1/platform/shopify/orders/create"))
        self.shopify_api.create_webhook("fulfillments/create",
                                        "%s%s" % (current_app.config.get('OPINEW_API_SERVER'),
                                                  "/api/v1/platform/shopify/orders/fulfill"))
        self.shopify_api.create_webhook("app/uninstalled",
                                        "%s%s" % (current_app.config.get('OPINEW_API_SERVER'),
                                                  "/api/v1/platform/shopify/app/uninstalled"))

    def import_products(self):
        # Get shopify products
        shopify_products_count = self.shopify_api.get_products_count()
        total_pages = shopify_products_count / Constants.SHOPIFY_MAX_PRODUCTS_PER_PAGE + 1
        for page in range(1, total_pages + 1):
            shopify_products = self.shopify_api.get_products(page=page)

            # Import shop products
            for shopify_product in shopify_products:
                product = self.adapter.product(shopify_product)
                if product:
                    product.shop = self.shop
                    g.db.add(product)
        g.db.push()

    def import_orders(self):
        shopify_orders_count = self.shopify_api.get_orders_count()
        total_pages = shopify_orders_count / Constants.SHOPIFY_MAX_ORDERS_PER_PAGE + 1
        for page in range(1, total_pages + 1):
            # Get shopify orders
            shopify_orders = self.shopify_api.get_orders(page=page)

            # Import shop orders
            for shopify_order in shopify_orders:
                order = self.adapter.order(shopify_order)
                if order:
                    order.shop = self.shop
                    g.db.add(order)
        g.db.push()

    def get_shop_name(self):
        if not len(self.shop.domain) > 14:
            raise ParamException('invalid shop domain', 400)
        shop_domain_ends_in = self.shop.domain[-14:]
        shop_name = self.shop.domain[:-14]
        if not shop_domain_ends_in or not shop_domain_ends_in == '.myshopify.com':
            raise ParamException('incorrect shop name', 400)
        return shop_name

    def shop_has_valid_token(self):
        webhooks_count = self.shopify_api.check_webhooks_count()
        # okay, the token is still valid!
        return webhooks_count == Constants.EXPECTED_WEBHOOKS

    def create_order(self, payload):
        platform_order_id = str(payload.get('id', ''))
        existing_order = models.Order.query.filter_by(platform_order_id=platform_order_id).first()
        if existing_order:
            raise exceptions.DbException('Order already exists', status_code=401)
        try:
            created_at_dt = date_parser.parse(payload.get('created_at')).astimezone(pytz.utc).replace(tzinfo=None)
        except:
            created_at_dt = datetime.datetime.utcnow()
        browser_ip = str(payload.get('browser_ip', ''))
        order = models.Order(platform_order_id=platform_order_id, shop=self.shop, purchase_timestamp=created_at_dt,
                             browser_ip=browser_ip)

        # try to speculatively find a FunnelStream to match for this order - from this browser IP, latest
        funnel_stream = None
        if browser_ip:
            funnel_stream = models.FunnelStream.query.filter_by(plugin_loaded_from_ip=browser_ip).order_by(
                models.FunnelStream.plugin_load_ts.desc()).first()
            if funnel_stream:
                funnel_stream.order = order
                db.session.add(funnel_stream)

        customer_email = payload.get('customer', {}).get('email')
        customer_name = "%s %s" % (
            payload.get('customer', {}).get('first_name', ''), payload.get('customer', {}).get('last_name', ''))
        existing_user = models.User.get_by_email_no_exception(customer_email)
        if existing_user:
            order.user = existing_user
        else:
            user_legacy, _ = models.UserLegacy.get_or_create_by_email(customer_email, name=customer_name)
            order.user_legacy = user_legacy

        line_items = payload.get('line_items', [])
        for line_item in line_items:
            platform_product_id = str(line_item.get('product_id'))
            product = models.Product.query.filter_by(platform_product_id=platform_product_id, shop=self.shop).first()
            if product:
                order.products.append(product)
            else:
                variant = models.ProductVariant.query.filter_by(
                    platform_variant_id=str(line_item.get('variant_id'))).first()
                if not variant:
                    continue
                order.products.append(variant.product)
            order.products.append(product)

        db.session.add(order)
        db.session.commit()

    def fulfill_order(self, payload):
        platform_order_id = str(payload.get('order_id', ''))

        order = models.Order.query.filter_by(platform_order_id=platform_order_id, shop=self.shop).first()
        delivery_tracking_number = payload.get('tracking_number')
        if order:
            created_at = payload.get('created_at')
            st = date_parser.parse(created_at).astimezone(pytz.utc).replace(tzinfo=None)
            if not order.status == Constants.ORDER_STATUS_SHIPPED:
                order.ship(delivery_tracking_number, shipment_timestamp=st)
                order.set_notifications()

    def shopify_shop_to_user_adapter(self, shopify_shop):
        shop_owner_email = shopify_shop.get('email', '')
        shop_owner_name = shopify_shop.get('shop_owner', '')
        return g.db.User.get_or_create_shop_owner(email=shop_owner_email,
                                                        name=shop_owner_name)

    def create_shop(self, shop_domain, hmac_request, code, nonce_request):
        client_id = current_app.config.get('SHOPIFY_APP_API_KEY')
        client_secret = current_app.config.get('SHOPIFY_APP_SECRET')

        # Initialize the API
        shopify_api = ShopifyAPI(client_id, client_secret)
        shopify_api.initialize_api(shop_domain=shop_domain, nonce_request=nonce_request, hmac_request=hmac_request,
                                   code=code)

        # Get shop and products info from API
        shopify_shop = shopify_api.get_shop()

        # Create db records
        # Create shop user, generate pass
        shop_owner = self.shopify_shop_to_user_adapter(shopify_shop)

        # Create shop with owner = shop_user
        shopify_platform = g.db.Platform.get_by_name(Constants.SHOPIFY_PLATFORM_NAME)
        shop = g.db.Shop.create(domain=shop_domain,
                                platform=shopify_platform,
                                access_token=shopify_api.access_token,
                                owner=shop_owner)
        self.shop = shop
        shop.name = self.get_shop_name()
        shop_owner.shops.append(shop)
        g.db.add(shop)

        # Create customer and subscribe to default plan
        shop_owner_customer = g.db.Customer.create(user=shop_owner)
        shopify_default_plan = g.db.Plan.get_by_name(name=Constants.SHOPIFY_DEFAULT_PLAN_NAME)
        subscription = g.db.Subscription.create(shop_owner_customer, shopify_default_plan, shop)
        g.db.add(subscription)

        g.db.push()

        # asyncronously create all products, orders and webhooks
        from async import tasks

        args = dict(shop_id=shop.id)
        task = models.Task.create(method=tasks.create_shopify_shop, args=args)
        g.db.add(task)
        g.db.push()
        return shop
