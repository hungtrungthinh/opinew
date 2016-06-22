"""
This module provides business-case classes which coordinate actions between
local database storage, remote data access through APIs and scheduling of asynchronous tasks.
"""
import datetime

from flask import url_for, current_app

from providers.platforms import ShopifyAPI
from providers.payment import StripeAPI
from webapp import db, models
from config import Constants


class Shopify(object):
    @classmethod
    def generate_oath_callback_url_for_shopify_app(cls, shop_domain):
        """
        Generate URL to redirect back to after a user has given permissions on the Shopify store
        """
        shop = models.Shop.get_by_domain(shop_domain)
        if shop:
            shopify_api = ShopifyAPI(shop=shop)
            if shopify_api.shop_has_valid_token():
                return url_for('client.shop_dashboard_id', shop_id=shop.id)

        shop_name = ShopifyAPI.get_shop_name_by_domain(shop_domain)

        client_id = current_app.config.get('SHOPIFY_APP_API_KEY')
        scopes = current_app.config.get('SHOPIFY_APP_SCOPES')

        nonce = shop_name

        redirect_uri = '%s/platforms/shopify/shops/create' % current_app.config.get('OPINEW_API_SERVER')

        url = 'https://{shop}/admin/oauth/authorize' \
              '?client_id={api_key}' \
              '&scope={scopes}' \
              '&redirect_uri={redirect_uri}' \
              '&state={nonce}'.format(
            shop=shop_domain, api_key=client_id, scopes=scopes, redirect_uri=redirect_uri, nonce=nonce)
        return url

    @classmethod
    def create_shopify_shop(cls, nonce_request, hmac_request, shop_domain, code):
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
        shop_owner_email = shopify_shop.get('email', '')
        shop_owner_name = shopify_shop.get('shop_owner', '')
        shop_owner = db.User.get_or_create_shop_owner(email=shop_owner_email,
                                                      name=shop_owner_name)

        # Create shop with owner = shop_user
        shopify_platform = db.Platform.get_by_name(Constants.SHOPIFY_PLATFORM_NAME)
        shop = db.Shop.create(domain=shop_domain,
                              platform=shopify_platform,
                              access_token=shopify_api.access_token,
                              owner=shop_owner)

        shop.name = ShopifyAPI.get_shop_name_by_domain(shop_domain)
        shop_owner.shops.append(shop)
        db.add(shop)

        # Create customer and subscribe to default plan
        shop_owner_customer = db.Customer.create(user=shop_owner)
        shopify_default_plan = db.Plan.get_by_name(name=Constants.SHOPIFY_DEFAULT_PLAN_NAME)
        subscription = db.Subscription.create(shop_owner_customer, shopify_default_plan, shop)
        db.add(subscription)

        db.commit()

        # schedule to get shop details
        cls.get_shop_details(shop)
        return shop

    @classmethod
    def get_shop_details(cls, shop):
        # asyncronously create all products, orders and webhooks
        from async import tasks

        args = dict(shop_id=shop.id)
        task = models.Task.create(method=tasks.create_shopify_shop, args=args)
        db.add(task)
        db.commit()


class User(object):
    @classmethod
    def create(cls, **kwargs):
        user = db.User.create(**kwargs)
        db.add(user)
        db.commit()


class Subscription(object):
    def create(self, customer, plan):
        timestamp = datetime.datetime.utcnow()
        stripe_subscription_id = StripeAPI.create_subscription(plan.stripe_plan_id,
                                                               customer.stripe_customer_id)
        subscription = models.Subscription(stripe_subscription_id=stripe_subscription_id,
                                           timestamp=timestamp)
        db.session.add(subscription)
        return self

    def update(self, plan):
        stripe_opinew_adapter = stripe_payment.StripeOpinewAdapter()
        self.stripe_subscription_id = stripe_opinew_adapter.update_subscription(self.customer.stripe_customer_id,
                                                                                self.stripe_subscription_id, plan)
        self.plan = plan
        return self

    def cancel(self):
        stripe_opinew_adapter = stripe_payment.StripeOpinewAdapter()
        stripe_opinew_adapter.cancel_subscription(self.customer.stripe_customer_id, self.stripe_subscription_id)
        now = datetime.datetime.utcnow()
        self.trialed_for = (now - self.timestamp).days
        self.plan = None
        self.timestamp = None
        self.stripe_subscription_id = None
