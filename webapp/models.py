from datetime import datetime
from sqlalchemy import and_
from sqlalchemy.orm import validates
from webapp import db, admin
from webapp.exceptions import DbException
from webapp.common import random_pwd
from flask import url_for, g, abort, redirect, request
from flask_admin.contrib.sqla import ModelView
from flask.ext.security import UserMixin, RoleMixin, current_user
from config import Constants

order_shop_products_table = db.Table('order_shop_products',
                                db.Column('order_id', db.Integer, db.ForeignKey('order.id')),
                                db.Column('shop_product_id', db.Integer, db.ForeignKey('shop_product.id'))
                                )

roles_users = db.Table('roles_users',
                       db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
                       db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
                       )


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __repr__(self):
        return '<Role %r>' % self.name


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String)
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))
    temp_password = db.Column(db.String)
    password = db.Column(db.String)
    name = db.Column(db.String)
    profile_picture_url = db.Column(db.String)

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

    def get_own_reviews_about_product_in_shop(self, product, shop):
        shop_product = ShopProduct.query.filter_by(shop=shop, product=product).first()
        return Review.query.filter_by(user=self, shop_product=shop_product).all()

    def get_notifications(self, start=0, stop=Constants.NOTIFICATIONS_INITIAL):
        return Notification.query.filter_by(user=self).order_by(Notification.id.desc()).all()[start:stop]

    @classmethod
    def get_by_id(cls, user_id):
        return cls.query.filter_by(id=user_id).first()

    @classmethod
    def get_by_email_no_exception(cls, email):
        return cls.query.filter_by(email=email).first()

    @classmethod
    def get_by_email(cls, email):
        user = cls.query.filter_by(email=email).first()
        if not user:
            raise DbException(message="User with email %s does not exist." % email, status_code=400)
        return user

    def unread_notifications(self):
        notifications = Notification.query.filter(and_(Notification.user_id == self.id,
                                                       Notification.is_read == False)).all()
        return len(notifications)

    def __repr__(self):
        return '<User %r>' % self.email


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("customer"), uselist=False)

    current_subscription_plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plan.id'))
    current_subscription_plan = db.relationship("SubscriptionPlan", backref=db.backref("customer"), uselist=False)

    stripe_token = db.Column(db.String)
    active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return '<Customer %r>' % self.user


class SubscriptionPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String)
    description = db.Column(db.String)
    price = db.Column(db.Integer)
    payment_frequency = db.Column(db.String)
    active = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<SubscriptionPlan %r>' % self.name


class CustomerSubscriptionPlanChange(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    customer = db.relationship("Customer", backref=db.backref("subscription_plan"), uselist=False)

    old_subscription_plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plan.id'))
    old_subscription_plan = db.relationship("SubscriptionPlan",
                                            primaryjoin="CustomerSubscriptionPlanChange.old_subscription_plan_id==SubscriptionPlan.id",
                                            backref=db.backref("plan_change_old", uselist=False),
                                            uselist=False)

    new_subscription_plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plan.id'))
    new_subscription_plan = db.relationship("SubscriptionPlan",
                                            primaryjoin="CustomerSubscriptionPlanChange.new_subscription_plan_id==SubscriptionPlan.id",
                                            backref=db.backref("plan_change_new", uselist=False),
                                            uselist=False)

    timestamp = db.Column(db.DateTime, default=datetime.utcnow())

    def __repr__(self):
        return '<PlanChange of %r from %r to %r>' % (self.customer, self.old_subscription_plan, self.new_subscription_plan)


class UserLikesReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    like_action = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("user_likes_review"), uselist=False)

    review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    review = db.relationship("Review", backref=db.backref("user_likes_review", uselist=False))


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


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    platform_order_id = db.Column(db.Integer)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("orders"))

    shop_products = db.relationship("ShopProduct", secondary=order_shop_products_table,
                                    backref=db.backref("orders", lazy="dynamic"))

    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    shop = db.relationship("Shop", backref=db.backref("orders"))

    delivery_tracking_number = db.Column(db.String)

    status = db.Column(db.String, default='PURCHASED')  # ['PURCHASED', 'SHIPPED', 'DELIVERED', 'NOTIFIED', 'REVIEWED']

    purchase_timestamp = db.Column(db.DateTime, default=datetime.utcnow())
    shipment_timestamp = db.Column(db.DateTime)
    delivery_timestamp = db.Column(db.DateTime)

    to_notify_timestamp = db.Column(db.DateTime)
    notification_timestamp = db.Column(db.DateTime)

    token = db.Column(db.String, default=random_pwd())

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

    def ship(self, delivery_tracking_number=None):
        self.status = 'SHIPPED'
        self.shipment_timestamp = datetime.utcnow()
        self.delivery_tracking_number = delivery_tracking_number
        # TODO: Update estimation
        db.session.add(self)
        db.session.commit()

    def deliver(self):
        self.status = 'DELIVERED'
        self.delivery_timestamp = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def notify(self):
        self.status = 'NOTIFIED'
        self.notification_timestamp = datetime.utcnow()
        for product in self.products:
            notification = Notification(user=self.user,
                                        content='We hope you love your new <b>%s</b>. <br>'
                                                'Could you spend a minute reviewing it?' % product.label,
                                        url=url_for('.web_review', order_id=self.id, product_id=product.id))
            db.session.add(notification)
        db.session.add(self)
        db.session.commit()


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String)
    created_ts = db.Column(db.DateTime, default=datetime.utcnow())
    photo_url = db.Column(db.String)
    by_customer_support = db.Column(db.Boolean, default=False)

    review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    review = db.relationship('Review', backref=db.backref('comments'))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("comments"))

    def __repr__(self):
        return '<Comment %r... for %r by %r>' % (self.body[:10], self.review, self.user)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.UnicodeText, default=u'')
    created_ts = db.Column(db.DateTime, default=datetime.utcnow())
    photo_url = db.Column(db.UnicodeText, default=u'')
    verified_review = db.Column(db.Boolean, default=False)
    by_shop_owner = db.Column(db.Boolean, default=False)
    star_rating = db.Column(db.Integer, default=0)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('reviews'))

    shop_product_id = db.Column(db.Integer, db.ForeignKey('shop_product.id'))
    shop_product = db.relationship('ShopProduct', backref=db.backref('reviews'))

    amending_review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    amending_review = db.relationship('Review', uselist=False, remote_side=[id],
                                      backref=db.backref('amended_review', uselist=False))

    def __init__(self, body=None, photo_url=None, shop_product_id=None, star_rating=None,
                 verified_review=None, by_shop_owner=None, **kwargs):
        self.body = body
        self.photo_url = photo_url
        self.shop_product_id = shop_product_id
        self.star_rating = star_rating
        self.verified_review = verified_review
        self.by_shop_owner = by_shop_owner

        self.user_id = current_user.id if current_user else 0

    @classmethod
    def create_from_repopulate(cls, user=None, shop_product_id=None, body=None, photo_url=None, star_rating=None,
                               verified_review=None):
        review = cls(body=body, photo_url=photo_url, shop_product_id=shop_product_id, star_rating=star_rating,
                     verified_review=verified_review)
        review.user = user
        return review

    @validates('star_rating')
    def validate_star_rating(self, key, rating):
        if rating:
            rating = int(rating)
            if rating >= 0 and rating <= 5:
                return rating
        raise DbException(message="[star_rating: Rating needs to be between 0 and 5 stars]", status_code=400)

    def __repr__(self):
        return '<Review %r... by %r>' % (self.body[:10], self.user)

    def is_for_shop(self, shop):
        if not self.order.shop == shop:
            raise DbException(message="This review is not for this shop", status_code=404)
        return True

    def is_approved_by_shop(self):
        shop_product_review = ShopProductReview.get_by_shop_and_review_id(self.shop_product.id, self.id)
        return shop_product_review.approved_by_shop

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
    def get_for_product(cls, product_id):
        shop_products = ShopProduct.query.filter(ShopProduct.product_id == product_id).all()
        return Review.query.filter(Review.shop_product_id.in_([sp.id for sp in shop_products])).order_by(
            Review.created_ts.desc()).all()

    @classmethod
    def get_for_product_approved_by_shop(cls, product_id, shop_id):
        shop_product = ShopProduct.query.filter(
            and_(ShopProduct.product_id == product_id, ShopProduct.shop_id == shop_id)).first()
        reviews = Review.query.filter_by(shop_product=shop_product).order_by(Review.created_ts.desc()).all()
        return [r for r in reviews if r.shop_product_review and r.shop_product_review.approved_by_shop]


class Shop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    domain = db.Column(db.String)

    access_token = db.Column(db.String)
    products_imported = db.Column(db.Boolean, default=False)

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
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
    def get_by_shop_domain(cls, shop_domain):
        shop = Shop.query.filter_by(domain=shop_domain).first()
        return shop

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


class Platform(db.Model):
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


class ShopProductReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    shop_product_id = db.Column(db.Integer, db.ForeignKey('shop_product.id'))
    shop_product = db.relationship("ShopProduct", backref=db.backref("shop_product_review", uselist=False))

    review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    review = db.relationship("Review", backref=db.backref("shop_product_review", uselist=False))

    approved_by_shop = db.Column(db.Boolean, default=False)
    approval_pending = db.Column(db.Boolean, default=True)

    @classmethod
    def get_by_shop_and_review_id(cls, shop_product_id, review_id):
        shop_product_review = cls.query.filter(
            and_(cls.shop_product_id == shop_product_id, cls.review_id == review_id)).first()
        if not shop_product_review:
            raise DbException(message='Shop %s does not have review %s' % (shop_product_id, review_id), status_code=400)
        return shop_product_review

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


class ShopProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String)
    platform_product_id = db.Column(db.Integer)

    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    shop = db.relationship("Shop", backref=db.backref("shop_product", uselist=False))

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship("Product", backref=db.backref("shop_product", uselist=False))

    @classmethod
    def get_by_shop_and_product_location(cls, shop_id, product_location):
        sp = cls.query.filter_by(shop_id=shop_id, url=product_location).first()
        if not sp or not sp.product:
            raise DbException(message='Shop_Product doesn\'t exist', status_code=404)
        return sp

    def __repr__(self):
        return '<%r - %r>' % (self.shop, self.product)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

    def __repr__(self):
        return '<Product %r>' % self.name

    def add_review(self, order, body, photo_url, shop_id):
        if order:
            user = User.get_by_email(order.user.email)
            shop_id = order.shop.id
        elif current_user.is_authenticated():
            user = current_user
            shop_id = shop_id
        else:
            user = None
            shop_id = None
        shop = Shop.get_by_id(shop_id)
        shop_product = ShopProduct.query.filter_by(product_id=self.id, shop_id=shop_id).first()
        review = Review(order=order, user=user, shop_product=shop_product,
                        photo_url=photo_url, body=body)
        shop_product_review = ShopProductReview(review=review, shop=shop)
        db.session.add(review)
        db.session.add(shop_product_review)
        db.session.commit()
        notification = Notification(user=shop.owner,
                                    content='You received a new review about <b>%s</b>. <br>'
                                            'Click here to allow or deny display on plugin' % review.shop_product.product.name,
                                    url=url_for('.view_review', review_id=review.id))
        db.session.add(notification)
        db.session.commit()
        return review

    @classmethod
    def get_by_id(cls, product_id):
        product = cls.query.filter(Product.id == product_id).first()
        if not product:
            raise DbException(message='Product doesn\'t exist', status_code=404)
        return product


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
admin.add_view(AdminModelView(Customer, db.session))
admin.add_view(AdminModelView(SubscriptionPlan, db.session))
admin.add_view(AdminModelView(CustomerSubscriptionPlanChange, db.session))
admin.add_view(AdminModelView(UserLikesReview, db.session))
admin.add_view(AdminModelView(Notification, db.session))
admin.add_view(AdminModelView(Order, db.session))
admin.add_view(AdminModelView(Comment, db.session))
admin.add_view(AdminModelView(Review, db.session))
admin.add_view(AdminModelView(Shop, db.session))
admin.add_view(AdminModelView(Platform, db.session))
admin.add_view(AdminModelView(ShopProductReview, db.session))
admin.add_view(AdminModelView(ShopProduct, db.session))
admin.add_view(AdminModelView(Product, db.session))
