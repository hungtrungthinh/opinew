"""
This module is responsible for defining the database models through a SQLAlchemy schema.
"""
from __future__ import division
import datetime
import re

import pytz
from dateutil import parser as date_parser
from sqlalchemy import and_
from flask import url_for, abort, redirect, request
from flask.ext.security.utils import encrypt_password
from flask_admin.contrib.sqla import ModelView
from flask.ext.security import UserMixin, RoleMixin, current_user
from flask_resize import resize

from webapp import db, admin, gravatar
from webapp.exceptions import DbException
from config import Constants
from webapp.common import generate_temp_password, random_pwd
from assets import strings

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

    unsubscribed = db.Column(db.Boolean, default=False)
    unsubscribe_token = db.Column(db.String)

    active = db.Column(db.Boolean, default=True)
    confirmed_at = db.Column(db.DateTime)
    last_login_at = db.Column(db.DateTime)
    current_login_at = db.Column(db.DateTime)
    last_login_ip = db.Column(db.String(40))
    current_login_ip = db.Column(db.String(40))
    login_count = db.Column(db.Integer)

    def get_notifications(self, start=0, stop=Constants.NOTIFICATIONS_INITIAL):
        return Notification.query.filter_by(user=self).order_by(Notification.id.desc()).all()[start:stop]

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

    unsubscribed = db.Column(db.Boolean, default=False)
    unsubscribe_token = db.Column(db.String)

    @classmethod
    def get_or_create_by_email(cls, email, **kwargs):
        is_new = False
        instance = cls.query.filter_by(email=email).first()
        if not instance:
            is_new = True
            instance = cls(email=email, **kwargs)
            db.session.add(instance)
            db.session.commit()
        return instance, is_new


class Customer(db.Model, Repopulatable):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("customer"), uselist=False)

    stripe_customer_id = db.Column(db.String)
    last4 = db.Column(db.String)
    active = db.Column(db.Boolean, default=True)

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

    def __repr__(self):
        return '<Plan %r>' % self.name


class Subscription(db.Model, Repopulatable):
    id = db.Column(db.Integer, primary_key=True)

    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    customer = db.relationship("Customer", backref=db.backref("subscription"), uselist=False)

    plan_id = db.Column(db.Integer, db.ForeignKey('plan.id'))
    plan = db.relationship("Plan", backref=db.backref("subscription"), uselist=False)

    timestamp = db.Column(db.DateTime)
    trialed_for = db.Column(db.Integer, default=0)

    stripe_subscription_id = db.Column(db.String)

    def __repr__(self):
        return '<Subscription of %r by %r>' % (self.plan, self.customer)


class ReviewLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    timestamp = db.Column(db.DateTime)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("review_likes"))

    review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    review = db.relationship("Review", backref=db.backref("likes"))


class ReviewReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    timestamp = db.Column(db.DateTime)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("review_reports"))

    review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    review = db.relationship("Review", backref=db.backref("reports"))


class ReviewFeature(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    timestamp = db.Column(db.DateTime)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("review_features"))

    review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    review = db.relationship("Review", backref=db.backref("featured"), uselist=False)


class ReviewShare(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    timestamp = db.Column(db.DateTime)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("review_shares"))

    review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    review = db.relationship("Review", backref=db.backref("shares"))

    def serialize(self):
        return {
            'action': True,
            'count': len(self.review.shares)
        }


class UrlReferer(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    timestamp = db.Column(db.DateTime)
    url = db.Column(db.String)
    q = db.Column(db.String)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("url_referers"))


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    content = db.Column(db.String)
    url = db.Column(db.String)
    is_read = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("notifications"))


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    celery_uuid = db.Column(db.String)
    eta = db.Column(db.DateTime)
    status = db.Column(db.String)

    method = db.Column(db.String)
    kwargs = db.Column(db.String)

    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    order = db.relationship("Order", backref=db.backref("tasks"))

    funnel_stream_id = db.Column(db.Integer, db.ForeignKey('funnel_stream.id'))
    funnel_stream = db.relationship("FunnelStream", backref=db.backref("tasks"))


class Order(db.Model, Repopulatable):
    id = db.Column(db.Integer, primary_key=True)

    platform_order_id = db.Column(db.String)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("orders"))

    user_legacy_id = db.Column(db.Integer, db.ForeignKey('user_legacy.id'))
    user_legacy = db.relationship("UserLegacy", backref=db.backref("orders"))

    products = db.relationship('Product', secondary=order_products_table,
                               backref=db.backref('orders', lazy='dynamic'))

    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    shop = db.relationship("Shop", backref=db.backref("orders"))

    browser_ip = db.Column(db.String)
    delivery_tracking_number = db.Column(db.String)
    discount = db.Column(db.String)

    status = db.Column(db.String,
                       default=Constants.ORDER_STATUS_PURCHASED)  # ['PURCHASED', 'SHIPPED', 'NOTIFIED', 'REVIEWED']

    purchase_timestamp = db.Column(db.DateTime)
    shipment_timestamp = db.Column(db.DateTime)

    to_notify_timestamp = db.Column(db.DateTime)
    notification_timestamp = db.Column(db.DateTime)

    funnel_stream_id = db.Column(db.Integer, db.ForeignKey('funnel_stream.id'))
    funnel_stream = db.relationship("FunnelStream", backref=db.backref("order", uselist=False))


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

    def serialize(self):
        return {
            'body': self.body,
            'user': {
                'name': self.user.name,
                'image_url': self.user.image_url
            }
        }


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
    from_customer = db.relationship('Customer', backref=db.backref('review_requests'))

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

    opened_timestamp = db.Column(db.DateTime)

    funnel_stream_id = db.Column(db.Integer, db.ForeignKey('funnel_stream.id'))
    funnel_stream = db.relationship("FunnelStream", backref=db.backref("review_requests"))


class RenderableObject(object):
    @property
    def object_type(self):
        return self.__class__.__name__


class Review(db.Model, Repopulatable, RenderableObject):
    id = db.Column(db.Integer, primary_key=True)

    body = db.Column(db.String)
    image_url = db.Column(db.String)
    star_rating = db.Column(db.Integer, default=0)

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship('Product', backref=db.backref('reviews'))

    # if review is about a shop in general
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    shop = db.relationship('Shop', backref=db.backref('reviews'))

    # CANNOT SET THESE BELOW:
    created_ts = db.Column(db.DateTime)
    deleted = db.Column(db.Boolean, default=False)
    deleted_ts = db.Column(db.DateTime)

    verified_review = db.Column(db.Boolean, default=False)
    by_shop_owner = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('reviews'))

    user_legacy_id = db.Column(db.Integer, db.ForeignKey('user_legacy.id'))
    user_legacy = db.relationship("UserLegacy", backref=db.backref("reviews"))

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

    funnel_stream_id = db.Column(db.Integer, db.ForeignKey('funnel_stream.id'))
    funnel_stream = db.relationship("FunnelStream", backref=db.backref("reviews"))



class Shop(db.Model, Repopulatable):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    description = db.Column(db.String)
    domain = db.Column(db.String)
    image_url = db.Column(db.String)
    active = db.Column(db.Boolean, default=True)

    automatically_approve_reviews = db.Column(db.Boolean, default=True)

    access_user = db.Column(db.String)
    access_token = db.Column(db.String)
    products_imported = db.Column(db.Boolean, default=False)

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                         default=current_user.id if current_user and current_user.is_authenticated() else None)
    owner = db.relationship("User", backref=db.backref("shops"))

    platform_id = db.Column(db.Integer, db.ForeignKey('platform.id'))
    platform = db.relationship("Platform", backref=db.backref("platform"))




    def __repr__(self):
        return '<Shop %r>' % self.name


class Platform(db.Model, Repopulatable):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

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
        for u in self.urls:
            if not u.is_regex:
                return u.url


class ProductUrl(db.Model, Repopulatable):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String)
    is_regex = db.Column(db.Boolean, default=False)

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship("Product", backref=db.backref("urls"))


class Question(db.Model, Repopulatable, RenderableObject):
    id = db.Column(db.Integer, primary_key=True)
    created_ts = db.Column(db.DateTime)

    body = db.Column(db.String)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("questions"))

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship("Product", backref=db.backref("questions"))

    click_count = db.Column(db.Integer, default=0)
    is_public = db.Column(db.Boolean, default=False)



class Answer(db.Model, Repopulatable):
    id = db.Column(db.Integer, primary_key=True)
    created_ts = db.Column(db.DateTime)

    body = db.Column(db.String)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("answers"))

    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    question = db.relationship("Question", backref=db.backref("answers"))


class SentEmail(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    timestamp = db.Column(db.DateTime)
    recipients = db.Column(db.String)
    subject = db.Column(db.String)
    template = db.Column(db.String)
    template_ctx = db.Column(db.String)
    body = db.Column(db.String)

    tracking_pixel_id = db.Column(db.String)
    opened_timestamp = db.Column(db.DateTime)

    for_shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    for_shop = db.relationship("Shop", backref=db.backref("emails_sent"))

    funnel_stream_id = db.Column(db.Integer, db.ForeignKey('funnel_stream.id'))
    funnel_stream = db.relationship("FunnelStream", backref=db.backref("sent_email", uselist=False))


class NextAction(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    timestamp = db.Column(db.DateTime)
    identifier = db.Column(db.String)
    title = db.Column(db.String)
    url = db.Column(db.String)
    icon = db.Column(db.String)
    icon_bg_color = db.Column(db.String)

    is_completed = db.Column(db.Boolean, default=False)
    completed_ts = db.Column(db.DateTime)

    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    shop = db.relationship("Shop", backref=db.backref("next_actions"))


class FunnelStream(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    shop = db.relationship("Shop", backref=db.backref("funnel_streams"))

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship("Product", backref=db.backref("funnel_streams"))

    # 1. First part of the funnel - page visits
    plugin_load_ts = db.Column(db.DateTime)
    plugin_loaded_from_ip = db.Column(db.String)

    # 2. How much interaction with our plugin
    plugin_glimpsed_ts = db.Column(db.DateTime)  # just part of the plugin is visible
    plugin_fully_seen_ts = db.Column(db.DateTime)  # the full plugin is visible
    plugin_mouse_hover_ts = db.Column(db.DateTime)
    plugin_mouse_scroll_ts = db.Column(db.DateTime)
    plugin_mouse_click_ts = db.Column(db.DateTime)

    # 3. Is there an order connected with this stream? Guess by timestamp and browser IP
    # 4. Task - on the backref of Task
    # 5. SentEmail - on the backref of SentEmail
    # 6. ReviewRequests - on the backref of ReviewRequest
    # 7. Reviews left - on the backref of review

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
admin.add_view(AdminModelView(ReviewShare, db.session))
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
admin.add_view(AdminModelView(SentEmail, db.session))
admin.add_view(AdminModelView(Source, db.session))
admin.add_view(AdminModelView(FunnelStream, db.session))
admin.add_view(AdminModelView(NextAction, db.session))
admin.add_view(AdminModelView(UrlReferer, db.session))
