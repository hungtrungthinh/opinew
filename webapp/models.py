import datetime
import re
import pytz
from dateutil import parser as date_parser
from sqlalchemy import and_
from webapp import db, admin
from webapp.exceptions import DbException
from async import stripe_payment
from flask import url_for, abort, redirect, request, current_app
from flask.ext.security.utils import encrypt_password
from flask_admin.contrib.sqla import ModelView
from flask.ext.security import UserMixin, RoleMixin, current_user
from config import Constants
from webapp import gravatar
from webapp.common import generate_temp_password, random_pwd

def create_review_requests(order_id):
    if not order_id:
        return
    order = Order.query.filter_by(id=order_id).first()
    if not order:
        return
    if not (order.shop and order.shop.owner and order.shop.owner.customer and order.shop.owner.customer[0]):
        return
    for product in order.products:
        the_user = order.user if order.user else (order.user_legacy if order.user_legacy else None)
        ReviewRequest.create(to_user=the_user,
                             from_customer=order.shop.owner.customer[0],
                             for_product=product,
                             for_order=order)

def schedule_notification_task(order_id, notify_dt):
    if not order_id or not notify_dt:
        return None
    order = Order.query.filter_by(id=order_id).first()
    if not order:
        return None
    from async import celery_async, tasks
    args = dict(order_id=order.id)
    celery_task = celery_async.schedule_task_at(tasks.notify_for_review, args, notify_dt)
    task_notify = Task(celery_uuid=celery_task.task_id,
                       status=celery_task.status,
                       eta=notify_dt,
                       method=celery_task.task_name,
                       kwargs=str(args))
    return task_notify

def schedule_email_task(order_id, notify_dt):
    if not order_id or not notify_dt:
        return None
    order = Order.query.filter_by(id=order_id).first()
    if not order:
        return None
    if not order.review_requests:
        return None
    from async import celery_async, tasks
    if order.user:
        recipients = [order.user.email]
    else:
        recipients = [order.user_legacy.email] if order.user_legacy else []
    template = current_app.config.get('DEFAULT_REVIEW_EMAIL_TEMPLATE')
    template_ctx = order.build_review_email_context()
    shop_name = order.shop.name if order.shop else Constants.DEFAULT_SHOP_NAME
    subject = Constants.DEFAULT_REVIEW_SUBJECT % (order.user.name.split()[0], shop_name)

    args = dict(recipients=recipients,
                template=template,
                template_ctx=template_ctx,
                subject=subject)
    celery_task = celery_async.schedule_task_at(tasks.send_email, args, notify_dt)
    task_email = Task(celery_uuid=celery_task.task_id,
                status=celery_task.status,
                eta=notify_dt,
                method=celery_task.task_name,
                kwargs=str(args))
    return task_email

order_products_table = db.Table('order_products',
                                db.Column('order_id', db.Integer, db.ForeignKey('order.id')),
                                db.Column('product_id', db.Integer, db.ForeignKey('product.id'))
                                )

roles_users_table = db.Table('roles_users',
                             db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
                             db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
                             )


class Repopulatable(object):
    def _is_datetime(self, value):
        try:
            return datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return value

    def from_repopulate(self, **kwargs):
        model_attributes = [a for a in dir(self) if not a[0] == '_']
        for attr, val in kwargs.iteritems():
            if attr in model_attributes and val:
                val = self._is_datetime(val)
                setattr(self, attr, val)
        return self


class Role(db.Model, RoleMixin, Repopulatable):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __repr__(self):
        return '<Role %r>' % self.name


class User(db.Model, UserMixin, Repopulatable):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String)
    roles = db.relationship("Role", secondary=roles_users_table,
                            backref=db.backref('users', lazy='dynamic'))
    is_shop_owner = db.Column(db.Boolean, default=False)
    temp_password = db.Column(db.String)
    password = db.Column(db.String)
    name = db.Column(db.String)
    image_url = db.Column(db.String)

    active = db.Column(db.Boolean, default=True)
    confirmed_at = db.Column(db.DateTime)
    last_login_at = db.Column(db.DateTime)
    current_login_at = db.Column(db.DateTime)
    last_login_ip = db.Column(db.String(40))
    current_login_ip = db.Column(db.String(40))
    login_count = db.Column(db.Integer)

    @classmethod
    def exclude_fields(cls):
        return ['user.active',
                'user.confirmed_at',
                'user.password',
                'user.stripe_token',
                'user.temp_password',
                'user.current_login_at',
                'user.current_login_ip',
                'user.last_login_at',
                'user.last_login_ip',
                'user.login_count']

    @classmethod
    def include_own_fields(cls):
        return ['id',
                'email',
                'name',
                'image_url']

    def get_notifications(self, start=0, stop=Constants.NOTIFICATIONS_INITIAL):
        return Notification.query.filter_by(user=self).order_by(Notification.id.desc()).all()[start:stop]

    @classmethod
    def get_by_id(cls, user_id):
        return cls.query.filter_by(id=user_id).first()

    @classmethod
    def get_by_email_no_exception(cls, email):
        return cls.query.filter_by(email=email).first()

    @property
    def reviews_count(self):
        return len(self.reviews)

    @property
    def likes_count(self):
        return len([rl for rl in ReviewLike.query.filter_by(user_id=self.id).all()])

    @classmethod
    def get_by_email(cls, email):
        user = cls.query.filter_by(email=email).first()
        if not user:
            raise DbException(message="User with email %s does not exist." % email, status_code=400)
        return user

    @classmethod
    def post_registration_handler(cls, *args, **kwargs):
        user = kwargs.get('user')
        if user.is_shop_owner:
            # append the role of a shop owner
            shop_role = Role.query.filter_by(name=Constants.SHOP_OWNER_ROLE).first()
            if shop_role and shop_role not in user.roles:
                user.roles.append(shop_role)
            gravatar_image_url = gravatar(user.email)
            if gravatar_image_url:
                user.image_url = gravatar_image_url
            # create a customer account
            plan = Plan.query.filter_by(name="Free").first()
            customer = Customer(user=user).create()
            subscription = Subscription(customer=customer, plan=plan).create()
            db.session.add(subscription)
        else:
            reviewer_role = Role.query.filter_by(name=Constants.REVIEWER_ROLE).first()
            if reviewer_role and reviewer_role not in user.roles:
                user.roles.append(reviewer_role)
        db.session.commit()

    @classmethod
    def get_or_create_by_email(cls, email, role_name=Constants.REVIEWER_ROLE, **kwargs):
        is_new = False
        instance = cls.query.filter_by(email=email).first()
        if not instance:
            is_new = True

            # Check for legacy user and merge if exists
            user_legacy = UserLegacy.query.filter_by(email=email).first()
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

            # Reassign the orders on legacy user:
            if user_legacy:
                for order in user_legacy.orders:
                    order.user_legacy = None
                    order.user = instance
                db.session.delete(user_legacy)

            # Check the role for the new user
            if role_name == Constants.SHOP_OWNER_ROLE:
                instance.is_shop_owner = True

            # Handle creation of customer and roles
            User.post_registration_handler(user=instance)

            # Send emailif
            from async import tasks

            tasks.send_email.delay(recipients=[email],
                                   template='email/new_user.html',
                                   template_ctx={'user_email': email,
                                                 'user_temp_password': temp_password,
                                                 'user_name': instance.name
                                                 },
                                   subject="Welcome to Opinew!")
        return instance, is_new

    def unread_notifications(self):
        notifications = Notification.query.filter(and_(Notification.user_id == self.id,
                                                       Notification.is_read == False)).all()
        return len(notifications)

    def __repr__(self):
        return '<User %r>' % self.email


class UserLegacy(db.Model, Repopulatable):
    """
    For the purposes of an order
    """
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String)
    is_shop_owner = db.Column(db.Boolean, default=False)
    name = db.Column(db.String)
    image_url = db.Column(db.String)

    @classmethod
    def get_or_create_by_email(cls, email, **kwargs):
        is_new = False
        instance = cls.query.filter_by(email=email).first()
        if not instance:
            is_new = True
            instance = cls(email=email, **kwargs)
        return instance, is_new


class Customer(db.Model, Repopulatable):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("customer"), uselist=False)

    stripe_customer_id = db.Column(db.String)
    last4 = db.Column(db.String)
    active = db.Column(db.Boolean, default=True)

    def create(self, **kwargs):
        stripe_opinew_adapter = stripe_payment.StripeOpinewAdapter()
        stripe_opinew_adapter.create_customer(self)
        return self

    def add_payment_card(self, stripe_token, **kwargs):
        stripe_opinew_adapter = stripe_payment.StripeOpinewAdapter()
        stripe_opinew_adapter.create_paying_customer(self, stripe_token)
        return self

    def __repr__(self):
        return '<Customer %r>' % self.user


class Plan(db.Model, Repopulatable):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String)
    description = db.Column(db.String)
    amount = db.Column(db.Integer)
    interval = db.Column(db.String)  # day, week, month or year
    trial_period_days = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=False)

    stripe_plan_id = db.Column(db.String)

    def create(self):
        stripe_opinew_adapter = stripe_payment.StripeOpinewAdapter()
        stripe_opinew_adapter.create_plan(self)
        return self

    def __repr__(self):
        return '<Plan %r>' % self.name


class Subscription(db.Model, Repopulatable):
    id = db.Column(db.Integer, primary_key=True)

    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    customer = db.relationship("Customer", backref=db.backref("subscription"), uselist=False)

    plan_id = db.Column(db.Integer, db.ForeignKey('plan.id'))
    plan = db.relationship("Plan", backref=db.backref("subscription"), uselist=False)

    timestamp = db.Column(db.DateTime)

    stripe_subscription_id = db.Column(db.String)

    def create(self):
        self.timestamp = datetime.datetime.utcnow()
        stripe_opinew_adapter = stripe_payment.StripeOpinewAdapter()
        stripe_opinew_adapter.create_subscription(self)
        return self

    @classmethod
    def update(cls, instance, plan):
        assert instance is not None
        stripe_opinew_adapter = stripe_payment.StripeOpinewAdapter()
        instance = stripe_opinew_adapter.update_subscription(instance, plan)
        return instance

    def __repr__(self):
        return '<Subscription of %r by %r>' % (self.plan, self.customer)


class ReviewLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    action = db.Column(db.Integer, default=1)
    timestamp = db.Column(db.DateTime)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                        default=current_user.id if current_user and current_user.is_authenticated() else 0)
    user = db.relationship("User", backref=db.backref("review_likes"))

    review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    review = db.relationship("Review", backref=db.backref("review_likes"))


class ReviewReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    action = db.Column(db.Integer, default=1)
    timestamp = db.Column(db.DateTime)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                        default=current_user.id if current_user and current_user.is_authenticated() else 0)
    user = db.relationship("User", backref=db.backref("review_reports"))

    review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    review = db.relationship("Review", backref=db.backref("review_reports"))


class ReviewFeature(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    action = db.Column(db.Integer, default=1)
    timestamp = db.Column(db.DateTime)

    review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    review = db.relationship("Review", backref=db.backref("feature"), uselist=False)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    content = db.Column(db.String)
    url = db.Column(db.String)
    is_read = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("notifications"))

    @classmethod
    def get_by_id(cls, notification_id):
        notification = cls.query.filter(Notification.id == notification_id).first()
        if not notification:
            raise DbException(message='Notification doesn\'t exist', status_code=404)
        return notification

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
            n_message = 'We hope you love your new <b>%s</b>. <br> Could do you like it?' % for_product.name
        elif for_shop:
            n_message = 'Thank you for shopping at <b>%s</b>. How did you like the experience?' % for_shop.name
        else:
            n_message = 'Up for some fun?'

        notification = cls(user=for_user,
                           content=n_message,
                           url='/%s' % token)
        db.session.add(notification)
        db.session.commit()

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    celery_uuid = db.Column(db.String)
    eta = db.Column(db.DateTime)
    status = db.Column(db.String)

    method = db.Column(db.String)
    kwargs = db.Column(db.String)

    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    order = db.relationship("Order", backref=db.backref("tasks"))


class Order(db.Model, Repopulatable):
    id = db.Column(db.Integer, primary_key=True)

    platform_order_id = db.Column(db.Integer)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("orders"))

    user_legacy_id = db.Column(db.Integer, db.ForeignKey('user_legacy.id'))
    user_legacy = db.relationship("UserLegacy", backref=db.backref("orders"))

    products = db.relationship('Product', secondary=order_products_table,
                               backref=db.backref('orders', lazy='dynamic'))

    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    shop = db.relationship("Shop", backref=db.backref("orders"))

    delivery_tracking_number = db.Column(db.String)
    discount = db.Column(db.String)

    status = db.Column(db.String,
                       default=Constants.ORDER_STATUS_PURCHASED)  # ['PURCHASED', 'SHIPPED', 'NOTIFIED', 'REVIEWED']

    purchase_timestamp = db.Column(db.DateTime)
    shipment_timestamp = db.Column(db.DateTime)

    to_notify_timestamp = db.Column(db.DateTime)
    notification_timestamp = db.Column(db.DateTime)

    def is_for_user(self, user):
        if not self.shop.user == user:
            raise DbException(message="This order is not for this user", status_code=403)
        return True

    @classmethod
    def get_by_id(cls, order_id):
        order = cls.query.filter_by(id=order_id).first()
        if not order:
            raise DbException(message='Order doesn\'t exist', status_code=404)
        return order

    def build_review_email_context(self):
        return {
            'order': self,
            'name': self.user.name.split()[0] if self.user else (self.user_legacy.name.split()[0] if self.user_legacy else ''),
            'user_email': self.user,
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

    def set_notifications(self):
        # Notify timestamp = shipment + 7
        notify_dt = self.shipment_timestamp + datetime.timedelta(days=Constants.DIFF_SHIPMENT_NOTIFY)
        self.to_notify_timestamp = notify_dt

        # is the notification in the past?
        now = datetime.datetime.utcnow()
        if now > self.to_notify_timestamp:
            return
        order_id = self.id
        create_review_requests(order_id=order_id)
        task_notify = schedule_notification_task(order_id=order_id , notify_dt=notify_dt)
        task_email = schedule_email_task(order_id=order_id, notify_dt=notify_dt)

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
                Notification.create(for_user=self.user, token=review_request.token, for_product=review_request.for_product)
        db.session.add(self)
        db.session.commit()

    def cancel_review(self):
        self.status = Constants.ORDER_STATUS_REVIEW_CANCELED
        for task in self.tasks:
            from async import celery_async
            if task:
                celery_async.revoke_task(task.celery_uuid)
                task.status = 'REVOKED'
                db.session.add(task)
        db.session.commit()


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String)
    created_ts = db.Column(db.DateTime, default=datetime.datetime.utcnow())
    image_url = db.Column(db.String)
    by_customer_support = db.Column(db.Boolean, default=False)

    review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    review = db.relationship('Review', backref=db.backref('comments'))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("comments"))

    def __repr__(self):
        return '<Comment %r... for %r by %r>' % (self.body[:10], self.review, self.user)


class Source(db.Model, Repopulatable):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

    def __repr__(self):
        return '<Source %r>' % self.name


class ReviewRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_ts = db.Column(db.DateTime)

    token = db.Column(db.String)

    from_customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    from_customer = db.relationship('Customer')

    to_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    to_user = db.relationship('User', backref=db.backref('review_requests'))

    to_user_legacy_id = db.Column(db.Integer, db.ForeignKey('user_legacy.id'))
    to_user_legacy = db.relationship('UserLegacy', backref=db.backref('review_requests'))

    for_product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    for_product = db.relationship('Product', backref=db.backref('review_requests'))

    for_shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    for_shop = db.relationship('Shop', backref=db.backref('review_requests'))

    for_order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    for_order = db.relationship('Order', backref=db.backref('review_requests'))

    received = db.Column(db.Boolean, default=False)
    completed = db.Column(db.Boolean, default=False)

    @classmethod
    def create(cls, to_user, from_customer, for_product=None, for_shop=None, for_order=None):
        while True:
            token = random_pwd(5)
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


class Review(db.Model, Repopulatable):
    id = db.Column(db.Integer, primary_key=True)

    body = db.Column(db.String)
    image_url = db.Column(db.String)
    star_rating = db.Column(db.Integer, default=0)

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship('Product', backref=db.backref('reviews'))

    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    shop = db.relationship('Shop', backref=db.backref('reviews'))

    # CANNOT SET THESE BELOW:
    created_ts = db.Column(db.DateTime)

    verified_review = db.Column(db.Boolean, default=False)
    by_shop_owner = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('reviews'))

    source_id = db.Column(db.Integer, db.ForeignKey('source.id'))
    source = db.relationship('Source', backref=db.backref('reviews'))

    source_url = db.Column(db.String)
    source_user_name = db.Column(db.String)
    source_user_image_url = db.Column(db.String)

    approved_by_shop = db.Column(db.Boolean, default=True)
    approval_pending = db.Column(db.Boolean, default=False)

    amending_review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    amending_review = db.relationship('Review', uselist=False, remote_side=[id],
                                      backref=db.backref('amended_review', uselist=False))

    youtube_video = db.Column(db.String)

    def __init__(self, body=None, image_url=None, star_rating=None, product_id=None, shop_id=None, verified_review=None,
                 user_id=None, **kwargs):
        self.body = unicode(body) if body else None
        self.image_url = image_url
        self.star_rating = star_rating
        if shop_id and product_id:
            raise DbException(message="[consistency: Can't set both shop_id and product_id]", status_code=400)
        self.product_id = product_id
        self.shop_id = shop_id
        self.verified_review = verified_review
        # Set automatic variables
        if current_user and current_user.is_authenticated():
            self.user = current_user
        if user_id:
            self.user = user_id
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
        excluded = []
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
    def likes(self):
        return sum([rl.action for rl in ReviewLike.query.filter_by(review_id=self.id).all()])

    @property
    def reports(self):
        return sum([rr.action for rr in ReviewReport.query.filter_by(review_id=self.id).all()])

    @property
    def liked_by_current_user(self):
        if current_user and current_user.is_authenticated():
            rl = ReviewLike.query.filter_by(review_id=self.id, user_id=current_user.id).first()
            return rl
        return False

    @property
    def reported_by_current_user(self):
        if current_user and current_user.is_authenticated():
            rr = ReviewReport.query.filter_by(review_id=self.id, user_id=current_user.id).first()
            return rr
        return False

    @property
    def featured(self):
        if current_user and current_user.is_authenticated():
            rf = ReviewFeature.query.filter_by(review_id=self.id).first()
            return rf
        return False

    @property
    def next_like_action(self):
        if current_user and current_user.is_authenticated():
            rl = ReviewLike.query.filter_by(review_id=self.id, user_id=current_user.id).first()
            return (0 if rl.action == 1 else 1) if rl else 1
        return 1

    @property
    def next_report_action(self):
        if current_user and current_user.is_authenticated():
            rr = ReviewReport.query.filter_by(review_id=self.id, user_id=current_user.id).first()
            return (0 if rr.action == 1 else 1) if rr else 1
        return 1

    @property
    def next_feature_action(self):
        if current_user and current_user.is_authenticated():
            rf = ReviewFeature.query.filter_by(review_id=self.id).first()
            return (0 if rf.action == 1 else 1) if rf else 1
        return 1

    def __repr__(self):
        return '<Review %r... by %r>' % (self.body[:10] if self.body else self.id, self.user)

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
        reviews = cls.query.order_by(Review.id.desc()).all()[start:end]
        return reviews

    @classmethod
    def get_by_user(cls, user_id):
        reviews = cls.query.filter_by(user_id=user_id).order_by(Review.id.desc()).all()
        return reviews


class Shop(db.Model, Repopulatable):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    description = db.Column(db.String)
    domain = db.Column(db.String)
    image_url = db.Column(db.String)

    automatically_approve_reviews = db.Column(db.Boolean, default=True)

    access_user = db.Column(db.String)
    access_token = db.Column(db.String)
    products_imported = db.Column(db.Boolean, default=False)

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                         default=current_user.id if current_user and current_user.is_authenticated() else None)
    owner = db.relationship("User", backref=db.backref("shops"))

    platform_id = db.Column(db.Integer, db.ForeignKey('platform.id'))
    platform = db.relationship("Platform", backref=db.backref("platform", uselist=False))

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
    def exists(cls, shop_id):
        shop = Shop.query.filter_by(id=shop_id).first()
        if not shop:
            raise DbException(message='Shop %s not registered with Opinew.' % shop_id, status_code=400)
        return True

    def is_owner(self, shop_user):
        if not shop_user.shop.id == self.id:
            raise DbException(message="User is not an owner of this shop", status_code=403)
        return True

    def __repr__(self):
        return '<Shop %r>' % self.name


class Platform(db.Model, Repopulatable):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

    @classmethod
    def get_by_name(cls, name):
        platform = cls.query.filter_by(name=name).first()
        if not platform:
            raise DbException(message='Platform %s not registered with Opinew.' % name, status_code=400)
        return platform

    def __repr__(self):
        return "<Platform %r>" % self.name

class ProductVariant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform_variant_id = db.Column(db.String)

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship("Product", backref=db.backref("variants"))


class Product(db.Model, Repopulatable):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    active = db.Column(db.Boolean, default=False)
    short_description = db.Column(db.String)
    product_type = db.Column(db.String)
    category = db.Column(db.String)
    image_url = db.Column(db.String)
    platform_product_id = db.Column(db.String)
    plugin_views = db.Column(db.Integer, default=0)
    review_help = db.Column(db.String)

    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    shop = db.relationship("Shop", backref=db.backref("products"))

    def __repr__(self):
        return '<Product %r>' % self.name

    @property
    def url(self):
        for url in self.urls:
            if not url.is_regex:
                return url.url

    @classmethod
    def get_by_id(cls, product_id):
        product = cls.query.filter(Product.id == product_id).first()
        if not product:
            raise DbException(message='Product doesn\'t exist', status_code=404)
        return product

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


class ProductUrl(db.Model, Repopulatable):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String)
    is_regex = db.Column(db.Boolean, default=False)

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship("Product", backref=db.backref("urls"))


class Question(db.Model, Repopulatable):
    id = db.Column(db.Integer, primary_key=True)

    body = db.Column(db.String)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("questions"))

    about_product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    about_product = db.relationship("Product", backref=db.backref("questions"))

    click_count = db.Column(db.Integer, default=0)
    is_public = db.Column(db.Boolean, default=False)


class Answer(db.Model, Repopulatable):
    id = db.Column(db.Integer, primary_key=True)

    body = db.Column(db.String)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("answers"))

    to_question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    to_question = db.relationship("Question", backref=db.backref("answers"))


# Create customized model view class
class AdminModelView(ModelView):
    def is_accessible(self):
        if not current_user.is_active() or not current_user.is_authenticated():
            return False

        if current_user.has_role(Constants.ADMIN_ROLE):
            return True

        return False

    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated():
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))

# Setup Flask-Admin
admin.add_view(AdminModelView(Role, db.session))
admin.add_view(AdminModelView(User, db.session))
admin.add_view(AdminModelView(UserLegacy, db.session))
admin.add_view(AdminModelView(Customer, db.session))
admin.add_view(AdminModelView(Plan, db.session))
admin.add_view(AdminModelView(Subscription, db.session))
admin.add_view(AdminModelView(ReviewLike, db.session))
admin.add_view(AdminModelView(ReviewReport, db.session))
admin.add_view(AdminModelView(ReviewFeature, db.session))
admin.add_view(AdminModelView(ReviewRequest, db.session))
admin.add_view(AdminModelView(Notification, db.session))
admin.add_view(AdminModelView(Order, db.session))
admin.add_view(AdminModelView(Comment, db.session))
admin.add_view(AdminModelView(Review, db.session))
admin.add_view(AdminModelView(Shop, db.session))
admin.add_view(AdminModelView(Platform, db.session))
admin.add_view(AdminModelView(Product, db.session))
admin.add_view(AdminModelView(ProductVariant, db.session))
admin.add_view(AdminModelView(ProductUrl, db.session))
admin.add_view(AdminModelView(Question, db.session))
admin.add_view(AdminModelView(Answer, db.session))
admin.add_view(AdminModelView(Task, db.session))
