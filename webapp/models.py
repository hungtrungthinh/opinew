from datetime import datetime
from sqlalchemy import and_
from sqlalchemy.orm import validates
from webapp import db, admin
from webapp.exceptions import DbException
from async import stripe_payment
from flask import url_for, g, abort, redirect, request
from flask_admin.contrib.sqla import ModelView
from flask.ext.security import UserMixin, RoleMixin, current_user
from config import Constants

order_products_table = db.Table('order_products',
                                db.Column('order_id', db.Integer, db.ForeignKey('order.id')),
                                db.Column('product_id', db.Integer, db.ForeignKey('product.id'))
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

    @classmethod
    def include_own_fields(cls):
        return ['id',
                'email',
                'name',
                'profile_picture_url']

    def get_own_reviews_about_product_in_shop(self, product, shop):
        return Review.query.filter_by(user=self, product=product).all()

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

    stripe_customer_id = db.Column(db.String)
    active = db.Column(db.Boolean, default=True)

    def __init__(self, stripe_token=None, **kwargs):
        super(Customer, self).__init__(**kwargs)
        stripe_opinew_adapter = stripe_payment.StripeOpinewAdapter()
        assert stripe_token is not None
        stripe_opinew_adapter.create_customer(self, stripe_token)

    def __repr__(self):
        return '<Customer %r>' % self.user


class Plan(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String)
    description = db.Column(db.String)
    amount = db.Column(db.Integer)
    interval = db.Column(db.String)  # day, week, month or year
    trial_period_days = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=False)

    stripe_plan_id = db.Column(db.String)

    def __init__(self, **kwargs):
        super(Plan, self).__init__(**kwargs)
        stripe_opinew_adapter = stripe_payment.StripeOpinewAdapter()
        stripe_opinew_adapter.create_plan(self)

    def __repr__(self):
        return '<Plan %r>' % self.name


class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    customer = db.relationship("Customer", backref=db.backref("subscription"), uselist=False)

    plan_id = db.Column(db.Integer, db.ForeignKey('plan.id'))
    plan = db.relationship("Plan", backref=db.backref("subscription"), uselist=False)

    timestamp = db.Column(db.DateTime, default=datetime.utcnow())

    stripe_subscription_id = db.Column(db.String)

    def __init__(self, **kwargs):
        super(Subscription, self).__init__(**kwargs)
        stripe_opinew_adapter = stripe_payment.StripeOpinewAdapter()
        stripe_opinew_adapter.create_subscription(self)

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
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                        default=current_user.id if current_user and current_user.is_authenticated() else 0)
    user = db.relationship("User", backref=db.backref("review_likes"))

    review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    review = db.relationship("Review", backref=db.backref("review_likes"))


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

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship("Product", backref=db.backref("orders"))

    review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    review = db.relationship("Review", backref=db.backref("order"))

    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    shop = db.relationship("Shop", backref=db.backref("orders"))

    delivery_tracking_number = db.Column(db.String)
    discount = db.Column(db.String)

    status = db.Column(db.String, default='PURCHASED')  # ['PURCHASED', 'SHIPPED', 'DELIVERED', 'NOTIFIED', 'REVIEWED']

    purchase_timestamp = db.Column(db.DateTime)
    shipment_timestamp = db.Column(db.DateTime)
    delivery_timestamp = db.Column(db.DateTime)

    to_notify_timestamp = db.Column(db.DateTime)
    notification_timestamp = db.Column(db.DateTime)

    token = db.Column(db.String)

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
    created_ts = db.Column(db.DateTime, default=datetime.utcnow())

    body = db.Column(db.UnicodeText, default=u'')
    photo_url = db.Column(db.UnicodeText, default=u'')
    star_rating = db.Column(db.Integer, default=0)

    verified_review = db.Column(db.Boolean, default=False)
    by_shop_owner = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('reviews'))

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship('Product', backref=db.backref('reviews'))

    amending_review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    amending_review = db.relationship('Review', uselist=False, remote_side=[id],
                                      backref=db.backref('amended_review', uselist=False))

    def __init__(self, body=None, photo_url=None, product_id=None, star_rating=None,
                 verified_review=None, by_shop_owner=None, **kwargs):
        self.body = body
        self.photo_url = photo_url
        self.product_id = product_id
        self.star_rating = star_rating
        self.verified_review = verified_review
        self.by_shop_owner = by_shop_owner

        self.user_id = current_user.id if current_user else 0

        db.session.add(self)
        db.session.commit()

        if self.user_id:
            user_like = ReviewLike(user_id=self.user_id, review_id=self.id)
            db.session.add(user_like)

        product_review = ProductReview(product_id=product_id, review_id=self.id)
        db.session.add(product_review)

        shop_owner = self.product.shop.owner
        notification = Notification(user=shop_owner,
                                    content='You received a new review about <b>%s</b>. <br>'
                                            'Click here to allow or deny display on plugin' % self.product.name,
                                    url='/review/%s' % self.id)
        db.session.add(notification)
        db.session.commit()

    @property
    def likes(self):
        return sum([rl.action for rl in ReviewLike.query.filter_by(review_id=self.id).all()])

    @property
    def liked_by_current_user(self):
        if current_user and current_user.is_authenticated():
            rl = ReviewLike.query.filter_by(review_id=self.id, user_id=current_user.id).first()
            return rl
        return False

    @property
    def next_like_action(self):
        if current_user and current_user.is_authenticated():
            rl = ReviewLike.query.filter_by(review_id=self.id, user_id=current_user.id).first()
            return (0 if rl.action == 1 else 1) if rl else 1
        return 1

    @classmethod
    def create_from_repopulate(cls, user_id=None, product_id=None, body=None, photo_url=None, star_rating=None,
                               verified_review=None):
        review = cls(body=body, photo_url=photo_url, product_id=product_id, star_rating=star_rating,
                     verified_review=verified_review)
        review.user_id = user_id
        user_like = ReviewLike(user_id=user_id, review_id=review.id)
        db.session.add(user_like)
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
        product_review = ProductReview.get_by_shop_and_review_id(self.product.id, self.id)
        return product_review.approved_by_shop

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
    def get_for_product_approved_by_shop(cls, product_id, shop_id):
        shop_product = Product.query.filter(
            and_(Product.id == product_id, Product.shop_id == shop_id)).first()
        reviews = Review.query.filter_by(product_id=product_id).order_by(Review.created_ts.desc()).all()
        return [r for r in reviews if r.product_review and r.product_review.approved_by_shop]


class Shop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    description = db.Column(db.String)
    domain = db.Column(db.String)

    automatically_approve_reviews = db.Column(db.Boolean, default=True)

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


class ProductReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship("Product", backref=db.backref("product_review", uselist=False))

    review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    review = db.relationship("Review", backref=db.backref("product_review", uselist=False))

    approved_by_shop = db.Column(db.Boolean, default=False)
    approval_pending = db.Column(db.Boolean, default=True)

    @classmethod
    def get_by_shop_and_review_id(cls, product_id, review_id):
        product_review = cls.query.filter(
            and_(cls.product_id == product_id, cls.review_id == review_id)).first()
        if not product_review:
            raise DbException(message='Product %s does not have review %s' % (product_id, review_id), status_code=400)
        return product_review

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


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    product_type = db.Column(db.String)
    url = db.Column(db.String)
    platform_product_id = db.Column(db.Integer)
    plugin_views = db.Column(db.Integer, default=0)
    review_help = db.Column(db.String)

    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    shop = db.relationship("Shop", backref=db.backref("products"))

    def __repr__(self):
        return '<Product %r>' % self.name

    @classmethod
    def get_by_id(cls, product_id):
        product = cls.query.filter(Product.id == product_id).first()
        if not product:
            raise DbException(message='Product doesn\'t exist', status_code=404)
        return product

    @classmethod
    def get_by_shop_and_product_location(cls, shop_id, product_location):
        product = cls.query.filter_by(shop_id=shop_id, url=product_location).first()
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
admin.add_view(AdminModelView(Plan, db.session))
admin.add_view(AdminModelView(Subscription, db.session))
admin.add_view(AdminModelView(ReviewLike, db.session))
admin.add_view(AdminModelView(Notification, db.session))
admin.add_view(AdminModelView(Order, db.session))
admin.add_view(AdminModelView(Comment, db.session))
admin.add_view(AdminModelView(Review, db.session))
admin.add_view(AdminModelView(Shop, db.session))
admin.add_view(AdminModelView(Platform, db.session))
admin.add_view(AdminModelView(ProductReview, db.session))
admin.add_view(AdminModelView(Product, db.session))
