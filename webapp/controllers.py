"""
This module provides business-case classes which coordinate actions between
local database storage, remote data access through APIs and scheduling of asynchronous tasks.
"""
from __future__ import division
import datetime
import httplib

from flask import url_for, current_app
from flask.ext.security import current_user

from providers.platforms import ShopifyAPI
from providers.payment import StripeAPI
from providers import giphy
from webapp import db, models
from config import Constants


def verify_required_condition(condition, error_msg, error_code=httplib.BAD_REQUEST,
                              error_category=Constants.ALERT_ERROR_LABEL):
    """
    Makes sure that the required condition is truthy. Otherwise raises a response error which is either
    jsonified response (if the resource has been required async) or flashing.
    :param condition: the condition
    :param error_msg: the error message to display
    :param error_code: the error code to return
    :return:
    """
    if not condition:
        raise RequirementException(message=error_msg, error_code=error_code, error_category=error_category)


def get_required_model_instance_by_id(model, instance_id):
    """
    Verifies and returns a model instance that is identified by id
    :param model: the Model to check
    :param instance_id: the instance id
    :return: a model instance by id
    """
    obj = model.query.filter_by(id=instance_id).first()
    verify_required_condition(condition=obj is not None,
                              error_msg=ExceptionMessages.INSTANCE_NOT_EXISTS.format(instance=model.__name__,
                                                                                     id=instance_id),
                              error_code=httplib.BAD_REQUEST)
    return obj


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

    @classmethod
    def post_registration_handler(cls, *args, **kwargs):
        user = kwargs.get('user')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        if user.is_shop_owner:
            # append the role of a shop owner
            shop_role = Role.query.filter_by(name=Constants.SHOP_OWNER_ROLE).first()
            if shop_role and shop_role not in user.roles:
                user.roles.append(shop_role)
            gravatar_image_url = gravatar(user.email)
            if gravatar_image_url:
                user.image_url = gravatar_image_url
            # create a customer account
            from async import tasks

            args = dict(user_id=user_id, plan_name=kwargs.get('plan_name'))
            task = Task.create(method=tasks.create_customer_account, args=args)
            db.session.add(task)
            email_template = Constants.DEFAULT_NEW_SHOP_OWNER_EMAIL_TEMPLATE
            email_subject = Constants.DEFAULT_NEW_SHOP_OWNER_SUBJECT
        else:
            email_template = Constants.DEFAULT_NEW_REVIEWER_EMAIL_TEMPLATE
            email_subject = Constants.DEFAULT_NEW_REVIEWER_SUBJECT
            reviewer_role = Role.query.filter_by(name=Constants.REVIEWER_ROLE).first()
            if reviewer_role and reviewer_role not in user.roles:
                user.roles.append(reviewer_role)
        if user and user.temp_password:
            from async import tasks

            args = dict(recipients=[user.email],
                        template=email_template,
                        template_ctx={'user_email': user.email,
                                      'user_temp_password': user.temp_password,
                                      'user_name': user.name
                                      },
                        subject=email_subject)
            task = Task.create(method=tasks.send_email, args=args)
            db.session.add(task)

            # set new next action
            now = datetime.datetime.utcnow()
            shop = user.shops[0] if user.shops else None
            if shop:
                im1 = NextAction(
                    shop=shop,
                    timestamp=now,
                    identifier=Constants.NEXT_ACTION_ID_SETUP_YOUR_SHOP,
                    title=strings.NEXT_ACTION_SETUP_YOUR_SHOP,
                    url=url_for('client.setup_plugin', shop_id=shop.id),
                    icon=Constants.NEXT_ACTION_SETUP_YOUR_SHOP_ICON,
                    icon_bg_color=Constants.NEXT_ACTION_SETUP_YOUR_SHOP_ICON_BG_COLOR
                )
                db.session.add(im1)

                im2 = NextAction(
                    timestamp=now,
                    shop=shop,
                    identifier=Constants.NEXT_ACTION_ID_SETUP_BILLING,
                    title=strings.NEXT_ACTION_SETUP_BILLING,
                    url="javascript:showTab('#account');",
                    icon=Constants.NEXT_ACTION_SETUP_BILLING_ICON,
                    icon_bg_color=Constants.NEXT_ACTION_SETUP_BILLING_ICON_BG_COLOR
                )
                db.session.add(im2)

                im3 = NextAction(
                    timestamp=now,
                    shop=shop,
                    identifier=Constants.NEXT_ACTION_ID_CHANGE_YOUR_PASSWORD,
                    title=strings.NEXT_ACTION_CHANGE_YOUR_PASSWORD,
                    url=url_for('security.change_password'),
                    icon=Constants.NEXT_ACTION_CHANGE_YOUR_PASSWORD_ICON,
                    icon_bg_color=Constants.NEXT_ACTION_CHANGE_YOUR_PASSWORD_ICON_BG_COLOR
                )
                db.session.add(im3)
        db.session.commit()

        @classmethod
        def get_or_create_by_email(cls, email, role_name=Constants.REVIEWER_ROLE, user_legacy_email=None,
                                   plan_name=None, **kwargs):
            is_new = False
            instance = cls.query.filter_by(email=email).first()
            if not instance:
                is_new = True

                # Check for legacy user and merge if exists
                user_legacy = None
                if user_legacy_email:
                    user_legacy = UserLegacy.query.filter_by(email=user_legacy_email).first()
                if user_legacy:
                    kwargs['name'] = kwargs.get('name') or user_legacy.name
                    kwargs['image_url'] = kwargs.get('image_url') or user_legacy.image_url

                # Generate temp password and encryption
                temp_password = generate_temp_password()
                encr_password = encrypt_password(temp_password)

                # Create an instance
                instance = cls(email=email,
                               temp_password=temp_password,
                               password=encr_password,
                               confirmed_at=datetime.datetime.utcnow(),
                               **kwargs)

                # Check the role for the new user
                if role_name == Constants.SHOP_OWNER_ROLE:
                    instance.is_shop_owner = True

                # Reassign the orders and review requests from legacy user
                if user_legacy:
                    cls.reassign_legacy_user_data_and_delete(user_legacy, instance)

                # Handle creation of customer and roles
                User.post_registration_handler(user=instance, plan_name=plan_name)
            return instance, is_new

        @classmethod
        def reassign_legacy_user_data_and_delete(cls, user_legacy, normal_user):
            # reassign the review requests
            review_requests = ReviewRequest.query.filter_by(to_user_legacy_id=user_legacy.id)
            for review_request in review_requests:
                review_request.to_user_legacy = None
                review_request.to_user = normal_user

            # reassign the orders
            for order in user_legacy.orders:
                order.user_legacy = None
                order.user = normal_user

            # reassign the reviews
            for review in user_legacy.reviews:
                review.user_legacy = None
                review.user = normal_user

            # delete legacy user
            db.session.delete(user_legacy)

        def unread_notifications(self):
            notifications = Notification.query.filter(and_(Notification.user_id == self.id,
                                                           Notification.is_read == False)).all()
            return len(notifications)


class Customer(object):
    def create(self, **kwargs):
        stripe_opinew_adapter = stripe_payment.StripeOpinewAdapter()
        self.stripe_customer_id = stripe_opinew_adapter.create_customer(self.user.email)
        return self

    def add_payment_card(self, stripe_token, **kwargs):
        stripe_opinew_adapter = stripe_payment.StripeOpinewAdapter()
        self.last4 = stripe_opinew_adapter.create_paying_customer(self, stripe_token)
        return self


class Plan(object):
    def create(self):
        stripe_opinew_adapter = stripe_payment.StripeOpinewAdapter()
        stripe_opinew_adapter.create_plan(self)
        return self


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


class Notification(object):
    def read(self):
        self.is_read = True
        db.session.add(self)
        db.session.commit()

    def is_for_user(self, user):
        if not self.user == user:
            raise DbException(message="Notification is not for logged in user", status_code=400)
        return True

    @classmethod
    def get_for_user(cls, user):
        if not user or not user.is_authenticated():
            raise DbException(message="User doesnt exist", status_code=400)
        return cls.query.filter_by(user=user).order_by(Notification.id.desc()).all()

    @classmethod
    def create(cls, for_user, token, for_product=None, for_shop=None):
        if for_product:
            n_message = 'We hope you love your new <b>%s</b>. <br> Could do you review it?' % for_product.name
        elif for_shop:
            n_message = 'Thank you for shopping at <b>%s</b>. How did you like the experience?' % for_shop.name
        else:
            n_message = 'Up for some fun?'

        notification = cls(user=for_user,
                           content=n_message,
                           url='/%s' % token)
        db.session.add(notification)
        db.session.commit()


class Task(object):
    @classmethod
    def create(cls, method, args, funnel_stream_id=None, eta=None):
        from async import celery_async
        task_instance = Task(method=method.__name__, eta=eta, kwargs=str(args), funnel_stream_id=funnel_stream_id)
        db.session.add(task_instance)
        db.session.commit()
        task_instance_id = task_instance.id
        # create the celery task
        if eta:
            celery_task = celery_async.schedule_task_at(method, args, eta, task_instance_id)
        else:
            celery_task = celery_async.delay_execute(method, args, task_instance_id)
        # Update task with celery id
        task_instance = Task.query.filter_by(id=task_instance_id).first()
        task_instance.celery_uuid = celery_task.task_id
        task_instance.status = celery_task.status
        return task_instance

    def revoke(self):
        from async import celery_async
        if self.celery_uuid:
            celery_async.revoke_task(self.celery_uuid)
        self.status = Constants.TASK_STATUS_REVOKED


class Order(object):
    def build_review_email_context(self):
        name = ''
        email = ''
        if self.user:
            if self.user.email:
                email = self.user.email
            if self.user.name:
                name = self.user.name.split()[0]
        elif self.user_legacy:
            if self.user_legacy.name:
                name = self.user_legacy.name.split()[0]
            if self.user_legacy.email:
                email = self.user_legacy.email
        return {
            'name': name,
            'user_email': email,
            'shop_name': self.shop.name if self.shop else '',
            'review_requests': [{'token': rr.token, 'product_name': rr.for_product.name} for rr in
                                self.review_requests],
        }

    def ship(self, delivery_tracking_number=None, shipment_timestamp=None):
        self.status = Constants.ORDER_STATUS_SHIPPED
        if shipment_timestamp and type(shipment_timestamp) is str:
            shipment_timestamp = date_parser.parse(shipment_timestamp).astimezone(pytz.utc).replace(tzinfo=None)
        self.shipment_timestamp = shipment_timestamp or datetime.datetime.utcnow()
        self.delivery_tracking_number = delivery_tracking_number
        db.session.add(self)
        db.session.commit()

    def create_review_requests(self, order_id):
        if not order_id:
            return
        order = Order.query.filter_by(id=order_id).first()
        if not order:
            return
        if not (order.shop and order.shop.owner and order.shop.owner.customer and order.shop.owner.customer[0]):
            return
        if not order.products:
            return
        # make sure we don't have repeating products
        product_review_requests = {}
        for product in order.products:
            if product.platform_product_id:
                product_review_requests[product.platform_product_id] = product
        for product in product_review_requests.values():
            the_user = order.user if order.user else (order.user_legacy if order.user_legacy else None)
            ReviewRequest.create(to_user=the_user,
                                 from_customer=order.shop.owner.customer[0],
                                 for_product=product,
                                 for_order=order)

    def schedule_notification_task(self, order_id, notify_dt):
        if not order_id or not notify_dt:
            return None
        order = Order.query.filter_by(id=order_id).first()
        if not order:
            return None
        from async import tasks

        args = dict(order_id=order.id)
        return Task.create(method=tasks.notify_for_review, args=args, eta=notify_dt)

    def schedule_email_task(self, order_id, notify_dt):
        if not order_id or not notify_dt:
            return None
        order = Order.query.filter_by(id=order_id).first()
        if not order:
            return None
        if not order.review_requests:
            return None
        if order.user:
            recipients = [order.user.email]
            user_name = order.user.name
        elif order.user_legacy:
            recipients = [order.user_legacy.email] if order.user_legacy else []
            user_name = order.user_legacy.name if order.user_legacy else ""
        else:
            return None
        template = Constants.DEFAULT_REVIEW_EMAIL_TEMPLATE
        template_ctx = order.build_review_email_context()
        shop_name = order.shop.name if order.shop else Constants.DEFAULT_SHOP_NAME
        subject = Constants.DEFAULT_REVIEW_SUBJECT % (user_name.split()[0] if user_name else '', shop_name)

        from async import tasks

        args = dict(recipients=recipients,
                    template=template,
                    template_ctx=template_ctx,
                    subject=subject,
                    funnel_stream_id=order.funnel_stream_id)
        return Task.create(method=tasks.send_email, args=args, eta=notify_dt, funnel_stream_id=order.funnel_stream_id)

    def set_notifications(self):
        if self.status == Constants.ORDER_STATUS_NOTIFIED:
            # should probably raise an exception here if we attmpted to notify again
            return
        # Notify timestamp = shipment + 7
        if self.shipment_timestamp is None:
            raise DbException(message="Shipment timestamp is None for this order: %d" % self.id, status_code=400)
        notify_dt = self.shipment_timestamp + datetime.timedelta(days=Constants.DIFF_SHIPMENT_NOTIFY)
        self.to_notify_timestamp = notify_dt

        # is the notification in the past?
        now = datetime.datetime.utcnow()
        if now > self.to_notify_timestamp:
            return

        if self.user is None and self.user_legacy is None:
            raise DbException(message="No user associated with this order: %d" % self.id, status_code=400)
        if self.shop is None:
            raise DbException(message="No shop associated with this order: %d" % self.id, status_code=400)
        if self.products is None or len(self.products) < 1:
            raise DbException(message="No products associated with this order: %d" % self.id, status_code=400)
        order_id = self.id
        self.create_review_requests(order_id=order_id)
        task_notify = self.schedule_notification_task(order_id=order_id, notify_dt=notify_dt)
        task_email = self.schedule_email_task(order_id=order_id, notify_dt=notify_dt)

        db.session.add(self)
        if task_notify:
            self.tasks.append(task_notify)
        if task_email:
            self.tasks.append(task_email)
        db.session.commit()

    def legacy(self):
        self.status = Constants.ORDER_STATUS_LEGACY
        db.session.add(self)
        db.session.commit()

    def notify(self):
        self.status = Constants.ORDER_STATUS_NOTIFIED
        self.notification_timestamp = datetime.datetime.utcnow()
        if self.user:
            for review_request in self.review_requests:
                Notification.create(for_user=self.user, token=review_request.token,
                                    for_product=review_request.for_product)
        db.session.add(self)
        db.session.commit()

    def cancel_review(self):
        for task in self.tasks:
            if task:
                task.revoke()
                db.session.add(task)
        self.status = Constants.ORDER_STATUS_REVIEW_CANCELED
        db.session.commit()


class ReviewRequest(object):
    @classmethod
    def create(cls, to_user, from_customer, for_product=None, for_shop=None, for_order=None):
        while True:
            token = random_pwd(Constants.REVIEW_REQUEST_TOKEN_LENGTH)
            rrold = ReviewRequest.query.filter_by(token=token).first()
            if not rrold:
                break
        kwargs = dict(created_ts=datetime.datetime.utcnow(),
                      token=token,
                      from_customer=from_customer,
                      for_shop=for_shop,
                      for_order=for_order,
                      for_product=for_product)
        if type(to_user) is UserLegacy:
            kwargs['to_user_legacy'] = to_user
        elif type(to_user) is User:
            kwargs['to_user'] = to_user
        rr = cls(**kwargs)
        db.session.add(rr)
        db.session.commit()
        return token

    @classmethod
    def get_by_token(cls, token):
        return models.ReviewRequest.query.filter_by(token=token).first()


class Review(object):
    def create(self, body=None, image_url=None, star_rating=None, product_id=None, shop_id=None, verified_review=None,
               user_id=None, **kwargs):
        self.body = unicode(body) if body else None
        self.image_url = image_url
        self.star_rating = star_rating

        if not body:
            if self.star_rating:
                self.body = Constants.DEFAULT_BODY_STARS.format(star_rating=star_rating)
            else:
                body = ""

        # differentiate between a review about a product vs a review about a shop
        if shop_id and product_id:
            raise DbException(message="[consistency: Can't set both shop_id and product_id]", status_code=400)
        self.product_id = product_id
        self.shop_id = shop_id
        self.verified_review = verified_review

        if user_id:
            self.user = User.query.filter_by(id=user_id).first()
        self.created_ts = datetime.datetime.utcnow()
        # Is it by shop owner?
        if product_id:
            product = Product.query.filter_by(id=product_id).first()
            if product and product.shop and product.shop.owner and product.shop.owner == current_user:
                self.by_shop_owner = True
        # Should we include youtube link?
        if self.body and (Constants.YOUTUBE_WATCH_LINK in self.body or Constants.YOUTUBE_SHORT_LINK in self.body):
            # we have youtube video somewhere in the body, let's extract it
            if Constants.YOUTUBE_WATCH_LINK in self.body:
                youtube_link = Constants.YOUTUBE_WATCH_LINK
            else:
                youtube_link = Constants.YOUTUBE_SHORT_LINK
            # find the youtube video id
            youtube_video_id = self.body.split(youtube_link)[1].split(' ')[0].split('?')[0].split('&')[0]
            self.youtube_video = Constants.YOUTUBE_EMBED_URL.format(youtube_video_id=youtube_video_id)
            # Finally, remove the link from the body
            to_remove = youtube_link + self.body.split(youtube_link)[1].split(' ')[0]
            self.body = re.sub(r"\s*" + re.escape(to_remove) + r"\s*", '', self.body)

    """
        We are assuming that the created_ts has type datetime (from python's datetime module)
        """

    @classmethod
    def create_from_import(cls, body=None, image_url=None, star_rating=None,
                           product_id=None, shop_id=None, verified_review=False, created_ts=None,
                           user=None, **kwargs):

        # go through Review.__init__()
        review = Review(body=body, image_url=image_url, star_rating=star_rating,
                        product_id=product_id, shop_id=shop_id, verified_review=verified_review)

        """
        Import specific things
        1.Deciding whether imported review's user is normal or legacy
        2.Setting up the review date
        3.Adding review to db
        """

        if isinstance(user, User):
            review.user = user
        elif isinstance(user, UserLegacy):
            review.user_legacy = user

        if created_ts:
            review.created_ts = created_ts

        db.session.add(review)
        db.session.commit()

        return review

    @classmethod
    def create_for_test(cls, source_user_name=None, source_id=None, user=None, **kwargs):
        review = Review(**kwargs)
        review.user = user
        review.source_user_name = source_user_name
        review.source_id = source_id
        return review

    @classmethod
    def verify_review_request(cls, data):
        review_request_id = data.get('review_request_id')
        if review_request_id:
            product_id = data.get('product_id')
            if not product_id:
                raise DbException(message='[Product_id required for review_request]', status_code=401)

            review_request_token = data.get('review_request_token')
            if not review_request_token:
                raise DbException(message='Review request token required', status_code=401)

            review_request = ReviewRequest.query.filter_by(id=review_request_id).first()
            if not review_request or not review_request.to_user == current_user:
                raise DbException(message='Not your review request', status_code=401)
            if not review_request_token == review_request.token:
                raise DbException(message='Wrong review request token', status_code=401)

            product = Product.query.filter_by(id=product_id).first()
            if not product or not product == review_request.for_product:
                raise DbException(message='Product not in order', status_code=401)
        return True

    @classmethod
    def exclude_fields(cls):
        excluded = ['shop.access_token']
        excluded += User.exclude_fields()
        return excluded

    def create(self, data=None):
        user_like = ReviewLike(user_id=self.user_id, review=self)
        db.session.add(user_like)

        shop_owner = self.product.shop.owner
        notification = Notification(user=shop_owner,
                                    content='You received a new review about <b>%s</b>. <br>'
                                            'Click here to allow or deny display on plugin' % self.product.name,
                                    url='/review/%s' % self.id)
        db.session.add(notification)
        return self

    @property
    def is_liked_by_current_user(self):
        if current_user and current_user.is_authenticated():
            review_like = ReviewLike.query.filter_by(review_id=self.id, user_id=current_user.id).first()
            if review_like:
                return True
        return False

    @property
    def is_reported_by_current_user(self):
        if current_user and current_user.is_authenticated():
            review_report = ReviewReport.query.filter_by(review_id=self.id, user_id=current_user.id).first()
            if review_report:
                return True
        return False

    @property
    def is_featured_by_current_user(self):
        if current_user and current_user.is_authenticated():
            review_feature = ReviewFeature.query.filter_by(review_id=self.id, user_id=current_user.id).first()
            if review_feature:
                return True
        return False

    @property
    def is_shared_by_current_user(self):
        if current_user and current_user.is_authenticated():
            review_shared = ReviewShare.query.filter_by(review_id=self.id, user_id=current_user.id).first()
            if review_shared:
                return True
        return False

    @property
    def user_name(self):
        if self.source_id and not self.source_id == 1 and self.source_user_name:
            _user_name = self.source_user_name
        elif self.user and self.user.name:
            _user_name = self.user.name
        else:
            _user_name = Constants.DEFAULT_ANONYMOUS_USER_NAME
        return _user_name

    @property
    def user_image_url(self):
        if self.user:
            if self.user.image_url:
                _user_image_url = self.user.image_url
            elif self.user.email:
                _user_image_url = gravatar(self.user.email)
            else:
                _user_image_url = gravatar('')
        elif self.source_id and not self.source_id == 1 and self.source_user_image_url:
            _user_image_url = self.source_user_image_url
        else:
            _user_image_url = gravatar('')
        return _user_image_url

    @classmethod
    def get_all_undeleted_reviews_for_product(cls, product_id):
        return cls.query.filter_by(product_id=product_id, deleted=False).all()

    def __repr__(self):
        return '<Review %r %r... by %r>' % (self.id, self.body[:10] if self.body else self.id, self.user)

    def is_for_shop(self, shop):
        if not self.order.shop == shop:
            raise DbException(message="This review is not for this shop", status_code=404)
        return True

    def approve(self):
        self.approved_by_shop = True
        self.approval_pending = False
        notification = Notification(user=self.review.user,
                                    content='The shop owner approved your review about <b>%s</b>.<br>'
                                            'View it here!' % self.shop_product.product.label,
                                    url=url_for('.get_product', product_id=self.shop_product.product.id))
        db.session.add(notification)
        db.session.add(self)
        db.session.commit()

    def disapprove(self):
        self.approved_by_shop = False
        self.approval_pending = False
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, review_id):
        review = Review.query.filter_by(id=review_id).first()
        if not review:
            raise DbException(message='Review doesn\'t exist', status_code=404)
        return review

    @classmethod
    def get_last(cls):
        review = Review.query.order_by(Review.id.desc()).first()
        if not review:
            raise DbException(message='Review doesn\'t exist', status_code=404)
        return review

    @classmethod
    def get_latest(cls, start, end):
        reviews = cls.query.filter_by(deleted=False).order_by(Review.id.desc()).all()[start:end]
        return reviews

    @classmethod
    def get_by_user(cls, user_id):
        reviews = cls.query.filter_by(user_id=user_id).order_by(Review.id.desc()).all()
        return reviews


class Shop(object):
    def update_access_token(self, access_token):
        self.access_token = access_token
        db.session.add(self)
        db.session.commit()

    def products_imported_complete(self):
        self.products_imported = True
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, shop_id):
        shop = Shop.query.filter_by(id=shop_id).first()
        if not shop:
            raise DbException(message='Shop %s not registered with Opinew.' % shop_id, status_code=400)
        return shop

    @classmethod
    def get_by_domain(cls, shop_domain):
        shop = Shop.query.filter_by(domain=shop_domain).first()
        if not shop:
            raise DbException(message='Shop %s not registered with Opinew.' % shop_domain, status_code=400)
        return shop

    @classmethod
    def exists(cls, shop_id):
        shop = Shop.query.filter_by(id=shop_id).first()
        if not shop:
            raise DbException(message='Shop %s not registered with Opinew.' % shop_id, status_code=400)
        return True

    def is_owner(self, shop_user):
        if not shop_user.shop.id == self.id:
            raise DbException(message="User is not an owner of this shop", status_code=403)
        return True

    def last_order_ts(self):
        return Order.query.filter_by(shop_id=self.id).order_by(Order.purchase_timestamp.desc()).first()

    def orders_before_opinew(self):
        owner_confirmed_at = self.owner.confirmed_at if self.owner and self.owner.confirmed_at else datetime.datetime.utcnow()
        return Order.query.filter(and_(Order.shop_id == self.id, Order.purchase_timestamp < owner_confirmed_at)).all()

    def orders_since_opinew(self):
        owner_confirmed_at = self.owner.confirmed_at if self.owner and self.owner.confirmed_at else datetime.datetime.utcnow()
        return Order.query.filter(and_(Order.shop_id == self.id, Order.purchase_timestamp >= owner_confirmed_at)).all()

    def get_stats(self):
        opinew_source = Source.query.filter_by(name='opinew').first()
        stats = {}

        orders_with_review_requests = []
        review_requests = []
        reviews = []
        reviews_cnt_by_product = {}

        verified_opinew_reviews = []
        opinew_total_reviews = []

        emails_converted = {}  # emails_with_at_least_one_rr_opened
        review_requests_opened_total = []

        for o in self.orders:
            if o.review_requests:
                orders_with_review_requests.append(o)

        for p in self.products:
            rs = p.reviews
            reviews += rs
            reviews_cnt = len(p.reviews)
            for r in rs:
                if r.source_id == opinew_source.id:
                    if r.verified_review:
                        verified_opinew_reviews.append(r)
                    opinew_total_reviews.append(r)
            rrs = p.review_requests
            review_requests += rrs
            for rr in rrs:
                if rr.opened_timestamp:
                    emails_converted[rr.for_order_id] = 1
                    review_requests_opened_total.append(rr)
            if reviews_cnt in reviews_cnt_by_product:
                reviews_cnt_by_product[reviews_cnt] += 1
            else:
                reviews_cnt_by_product[reviews_cnt] = 1

        funnel_streams_glimpsed = []
        funnel_streams_fully_seen = []
        funnel_streams_hovered = []
        funnel_streams_scrolled = []
        funnel_streams_clicked = []
        for fs in self.funnel_streams:
            if fs.plugin_glimpsed_ts:
                funnel_streams_glimpsed.append(fs.plugin_glimpsed_ts)
            if fs.plugin_fully_seen_ts:
                funnel_streams_fully_seen.append(fs.plugin_fully_seen_ts)
            if fs.plugin_mouse_hover_ts:
                funnel_streams_hovered.append(fs.plugin_mouse_hover_ts)
            if fs.plugin_mouse_scroll_ts:
                funnel_streams_scrolled.append(fs.plugin_mouse_scroll_ts)
            if fs.plugin_mouse_click_ts:
                funnel_streams_clicked.append(fs.plugin_mouse_click_ts)

        stats['since'] = self.owner.confirmed_at if self.owner else 0

        stats['orders_with_review_requests'] = orders_with_review_requests
        stats['orders_with_review_requests_cnt'] = len(stats['orders_with_review_requests'])

        stats['review_requests'] = review_requests
        stats['review_requests_cnt'] = len(stats['review_requests'])

        stats['reviews'] = reviews
        stats['reviews_cnt'] = len(stats['reviews'])
        stats['reviews_cnt_by_product'] = sorted(reviews_cnt_by_product.items(), key=lambda t: t[0], reverse=True)

        stats['funnel_streams'] = self.funnel_streams
        stats['funnel_streams_cnt'] = len(self.funnel_streams)
        stats['funnel_streams_glimpsed_cnt'] = len(funnel_streams_glimpsed)
        stats['funnel_streams_fully_seen_cnt'] = len(funnel_streams_fully_seen)
        stats['funnel_streams_hovered_cnt'] = len(funnel_streams_hovered)
        stats['funnel_streams_scrolled_cnt'] = len(funnel_streams_scrolled)
        stats['funnel_streams_clicked_cnt'] = len(funnel_streams_clicked)

        stats['emails_sent'] = self.emails_sent
        stats['emails_sent_cnt'] = len(stats['emails_sent'])

        stats['emails_opened'] = [e.opened_timestamp for e in self.emails_sent if e.opened_timestamp]
        stats['emails_opened_cnt'] = len(stats['emails_opened'])

        stats['emails_opened_over_sent_pctg'] = (stats['emails_opened_cnt'] / stats['emails_sent_cnt']) * 100 if stats[
            'emails_sent_cnt'] else '-'

        stats['emails_converted'] = emails_converted
        stats['emails_converted_cnt'] = len(stats['emails_converted'])
        stats['emails_converted_over_emails_opened_pctg'] = (stats['emails_converted_cnt'] / stats[
            'emails_opened_cnt']) * 100 if stats['emails_opened_cnt'] else '-'

        stats['verified_opinew_reviews'] = verified_opinew_reviews
        stats['verified_opinew_reviews_cnt'] = len(stats['verified_opinew_reviews'])
        stats['verified_opinew_reviews_over_email_converted_pctg'] = (stats['verified_opinew_reviews_cnt'] / stats[
            'emails_converted_cnt']) * 100 if stats['emails_converted_cnt'] else '-'

        stats['review_requests_opened_total'] = review_requests_opened_total
        stats['review_requests_opened_total_cnt'] = len(stats['review_requests_opened_total'])

        stats['opinew_total_reviews'] = opinew_total_reviews
        stats['opinew_total_reviews_cnt'] = len(stats['opinew_total_reviews'])
        return stats


class Product(object):
    @classmethod
    def find_product_by_url(cls, product_url, shop_id):
        product_candidate = ProductUrl.query.filter_by(url=product_url, is_regex=False).first()
        if product_candidate and \
                product_candidate.product and \
                product_candidate.product.shop_id:
            if product_candidate.product.shop_id == int(shop_id):
                return product_candidate.product
        else:
            product_candidates = Product.query.filter_by(shop_id=shop_id).all()
            for product_candidate in product_candidates:
                for url in product_candidate.urls:
                    if url.is_regex:
                        url_regex = re.compile(url.url)
                        match = re.match(url_regex, product_url)
                        if match:
                            return product_candidate


class Question(object):
    @classmethod
    def get_all_questions_for_product(cls, product_id):
        return cls.query.filter_by(product_id=product_id).all()


class Giphy(object):
    @classmethod
    def get_trending(cls):
        giphy_api_key = current_app.config.get('GIPHY_API_KEY')
        return giphy.get_trending(giphy_api_key)

    @classmethod
    def get_by_query(cls, query, limit, offset):
        giphy_api_key = current_app.config.get('GIPHY_API_KEY')
        return giphy.get_by_query(giphy_api_key, query, limit, offset)


def calculate_regular_review_score(review, timestamp):
    # Calculate days between now and the post of the review.
    days_since = (timestamp - review.created_ts).days
    # Older reviews are penalized
    review.rank_score -= days_since * Constants.REVIEW_RANK_DAYS_WEIGHT
    if review.user:
        # Promote liked users
        review.rank_score += len(review.user.reviews) * Constants.REVIEW_RANK_USER_LIKES_WEIGHT
        # Promote users with more reviews
        review.rank_score += len(review.user.review_likes) * Constants.REVIEW_RANK_USER_REVIEWS_WEIGHT
    # Promote reviews with more likes
    review.rank_score += len(review.likes) * Constants.REVIEW_RANK_LIKES_WEIGHT
    # Promote reviews with more shares
    review.rank_score += len(review.shares) * Constants.REVIEW_RANK_SHARES_WEIGHT
    # Promote reviews with more comments
    review.rank_score += len(review.comments) * Constants.REVIEW_RANK_COMMENTS_WEIGHT
    # Penalize reviews with more reports
    review.rank_score -= len(review.reports) * Constants.REVIEW_RANK_REPORTS_WEIGHT
    # Promote verified reviews
    review.rank_score += Constants.REVIEW_RANK_IS_VERIFIED_WEIGHT if review.verified_review else 0
    # Promote reviews with images
    review.rank_score += Constants.REVIEW_RANK_HAS_IMAGE_WEIGHT if review.image_url else 0
    # Promote reviews with videos
    review.rank_score += Constants.REVIEW_RANK_HAS_VIDEO_WEIGHT if review.youtube_video else 0


def calculate_question_score(question, timestamp):
    # Calculate days between now and the post of the review.
    days_since = (timestamp - question.created_ts).days
    # Older reviews are penalized
    question.rank_score -= days_since * Constants.QUESTION_RANK_DAYS_WEIGHT


def rank_objects_for_product(product_id):
    now = datetime.datetime.utcnow()
    own_review = []
    featured_reviews = []
    regular_reviews = []
    questions = []
    star_distribution = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    star_rating_sum = 0
    reviews_with_stars = 0

    # Get all not deleted reviews
    all_reviews = models.Review.get_all_undeleted_reviews_for_product(product_id)
    for review in all_reviews:
        if review.star_rating:
            star_distribution[review.star_rating] += 1
            reviews_with_stars += 1
            star_rating_sum += review.star_rating
        review.rank_score = 0
        if review.user == current_user:
            own_review = [review]
        elif review.featured:
            featured_reviews.append(review)
        else:
            calculate_regular_review_score(review, timestamp=now)
            # Add it to regular reviews
            regular_reviews.append(review)

    # Get all questions
    all_questions = models.Question.get_all_questions_for_product(product_id)
    for question in all_questions:
        question.rank_score = 0
        calculate_question_score(question, timestamp=now)
        # Add it to list of questions
        questions.append(question)

    # Merge questions and regular reviews
    question_review_rank = questions + regular_reviews

    # Sort by rank_score
    question_review_rank = sorted(question_review_rank, key=lambda x: x.rank_score, reverse=True)
    final_rank = own_review + featured_reviews + question_review_rank

    # calculate average stars:
    total_reviews = len(own_review + featured_reviews + regular_reviews)
    average_stars = star_rating_sum / reviews_with_stars if reviews_with_stars else 0

    return {
        'total_reviews': total_reviews,
        'objs_list': final_rank,
        'average_stars': average_stars,
        'main_star_distribution': star_distribution
    }


def get_incoming_messages(shop):
    return models.NextAction.query.filter_by(shop=shop, is_completed=False).all()


def get_scheduled_tasks(shop):
    scheduled_tasks = []
    for order in shop.orders:
        for task in order.tasks:
            if task.status == "PENDING":
                obj = {
                    'title': task.method,
                    'icon': 'envelope',
                    'eta': task.eta,
                    'user': order.user,
                    'products': order.products
                }
                scheduled_tasks.append(obj)
    return sorted(scheduled_tasks, key=lambda x: x['eta'])


def get_reviews(shop):
    reviews = []
    for product in shop.products:
        reviews += models.Review.query.filter_by(product=product).all()
    return reviews


def get_analytics(shop):
    analytics = shop.get_stats()
    return analytics
