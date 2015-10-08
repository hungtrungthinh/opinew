from datetime import datetime
from sqlalchemy import and_
from webapp import db, login_manager
from webapp.common import generate_temp_password
from webapp.exceptions import DbException
from flask import url_for, g
from flask.ext.login import current_user
from flask.ext.login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config, Constants
from async import email_sender

product_tags_table = db.Table('product_tags',
                              db.Column('product_id', db.Integer, db.ForeignKey('product.id')),
                              db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
                              )

review_tags_table = db.Table('review_tags',
                             db.Column('review_id', db.Integer, db.ForeignKey('review.id')),
                             db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
                             )

order_products_table = db.Table('order_products',
                                db.Column('order_id', db.Integer, db.ForeignKey('order.id')),
                                db.Column('product_id', db.Integer, db.ForeignKey('product.id'))
                                )


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)



class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String)
    role = db.Column(db.String)
    password = db.Column(db.String)
    temp_password = db.Column(db.String)
    pw_hash = db.Column(db.String)
    name = db.Column(db.String)
    profile_picture_url = db.Column(db.String)
    stripe_token = db.Column(db.String)

    def __init__(self, email=None, name=None, profile_picture_url=Config.DEFAULT_PROFILE_PICTURE,
                 password=None, role=None, stripe_token=None, **kwargs):
        self.email = email
        if not password:
            self.temp_password = generate_temp_password()
            self.password = self.temp_password
            self.pw_hash = generate_password_hash(self.temp_password)
        else:
            self.pw_hash = generate_password_hash(password)
            self.password = password
        self.name = name
        self.profile_picture_url = profile_picture_url
        self.role = role
        self.stripe_token = stripe_token

    def get_own_reviews_about_product_in_shop(self, product, shop):
        shop_product = ShopProduct.query.filter_by(shop=shop, product=product).first()
        return Review.query.filter_by(user=self, shop_product=shop_product).all()

    def get_notifications(self, start=0, stop=Constants.NOTIFICATIONS_INITIAL):
        return Notification.query.filter_by(user=self).order_by(Notification.id.desc()).all()[start:stop]

    @classmethod
    def get_by_id(cls, user_id):
        return cls.query.filter_by(id=user_id).first()

    @classmethod
    def get_or_create_by_email(cls, email):
        user = cls.query.filter_by(email=email).first()
        if not user:
            user = User(email=email, role=Constants.REVIEWER_ROLE)
            db.session.add(user)
            db.session.commit()
            if not g.mode == 'development':
                email_sender.send_mail(email, "Welcome to Opinew", "new_user.html", {'user_password': user.temp_password},)
        return user

    @classmethod
    def get_by_email(cls, email):
        user = cls.query.filter_by(email=email).first()
        if not user:
            raise DbException(message="User with email %s does not exist." % email, status_code=400)
        return user

    def validate_password(self, password):
        if not check_password_hash(self.pw_hash, password):
            raise DbException(message="Wrong password.", status_code=400)
        return True

    def unread_notifications(self):
        notifications = Notification.query.filter(and_(Notification.user_id == self.id,
                                                       Notification.is_read == False)).all()
        return len(notifications)

    def __repr__(self):
        return '<User %r>' % self.id

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'profile_picture_url': self.profile_picture_url
        }

    def serialize_with_pass(self):
        return {
            'id': self.id,
            'email': self.email,
            'password': self.password,
        }


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    content = db.Column(db.String)
    url = db.Column(db.String)
    is_read = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("notifications"))

    def __init__(self, content=None, url=None, user=None):
        self.content = content
        self.url = url
        self.user = user

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
        return cls.query.filter_by(user=user).order_by(Notification.id.desc()).all()

    def serialize(self):
        return {
            'id': self.id,
            'url': self.url,
            'read_status': self.is_read,
            'ntype': self.ntype,
            'meta': self.order.serialize() if self.order else self.review.serialize_with_product(),
        }


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    platform_order_id = db.Column(db.Integer)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("orders"))

    products = db.relationship("Product", secondary=order_products_table,
                               backref=db.backref("orders", lazy="dynamic"))

    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    shop = db.relationship("Shop", backref=db.backref("orders"))

    delivery_tracking_number = db.Column(db.String)

    status = db.Column(db.String)  # ['PURCHASED', 'SHIPPED', 'DELIVERED', 'NOTIFIED', 'REVIEWED']

    purchase_timestamp = db.Column(db.DateTime)
    shipment_timestamp = db.Column(db.DateTime)
    delivery_timestamp = db.Column(db.DateTime)

    to_notify_timestamp = db.Column(db.DateTime)
    notification_timestamp = db.Column(db.DateTime)

    def __init__(self, platform_order_id=None, user=None, shop=None):
        self.platform_order_id = platform_order_id
        self.user = user
        self.shop = shop

        self.status = 'PURCHASED'
        self.purchase_timestamp = datetime.utcnow()

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

    @classmethod
    def get_by_shop_product_user(cls, shop_id, product_id, user_id):
        order = Order.query.filter(and_(Order.shop_id == shop_id,
                                        Order.product_id == product_id,
                                        Order.user_id == user_id)).first()
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

    def serialize(self):
        return {
            'id': self.id,
            'user': self.user.serialize(),
            'products': self.product.serialize(),
            'shop': self.shop.serialize(),
            'status': self.status,
            'purchase_timestamp': self.purchase_timestamp,
            'shipment_timestamp': self.shipment_timestamp,
            'delivery_timestamp': self.delivery_timestamp,
            'notification_timestamp': self.notification_timestamp
        }


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String)
    created_ts = db.Column(db.DateTime)
    photo_url = db.Column(db.String)

    tags = db.relationship("Tag", secondary=review_tags_table, backref=db.backref("reviews", lazy="dynamic"))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('reviews'))

    shop_product_id = db.Column(db.Integer, db.ForeignKey('shop_product.id'))
    shop_product = db.relationship('ShopProduct', backref=db.backref('reviews'))

    def __init__(self, user=None, shop_product=None, order=None, body=None, photo_url=None, **kwargs):
        self.user = user
        self.order = order
        self.body = body
        self.photo_url = photo_url
        self.created_ts = datetime.utcnow()
        self.shop_product = shop_product

    def __repr__(self):
        return '<Review %r>' % self.body

    def serialize(self):
        return {
            'id': self.id,
            'body': self.body,
            'photo_url': self.photo_url,
            'tags': [t.serialize() for t in self.tags],
            'user': self.user.serialize() if self.user else None
        }

    def serialize_with_product(self):
        return {
            'id': self.id,
            'body': self.body,
            'photo_url': self.photo_url,
            'tags': [t.serialize() for t in self.tags],
            'user': self.user.serialize() if self.user else None,
            'product': self.shop_product.product.serialize() if self.shop_product and self.shop_product.product else None
        }

    def is_for_shop(self, shop):
        if not self.order.shop == shop:
            raise DbException(message="This review is not for this shop", status_code=404)
        return True

    def is_approved_by_shop(self):
        shop_review = ShopReview.get_by_shop_and_review_id(self.shop_product.shop.id, self.id)
        return shop_review.approved_by_shop

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
        shop_products = ShopProduct.query.filter(ShopProduct.product_id==product_id).all()
        return Review.query.filter(Review.shop_product_id.in_([sp.id for sp in shop_products])).order_by(Review.created_ts.desc()).all()

    @classmethod
    def get_for_product_approved_by_shop(cls, product_id, shop_id):
        shop_product = ShopProduct.query.filter(and_(ShopProduct.product_id==product_id, ShopProduct.shop_id==shop_id)).first()
        reviews = Review.query.filter_by(shop_product=shop_product).order_by(Review.created_ts.desc()).all()
        return [r for r in reviews if r.shop_review.approved_by_shop]


class Shop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String)
    domain = db.Column(db.String)

    access_token = db.Column(db.String)
    products_imported = db.Column(db.Boolean, default=False)

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship("User", backref=db.backref("shop", uselist=False))

    platform_id = db.Column(db.Integer, db.ForeignKey('platform.id'))
    platform = db.relationship("Platform", backref=db.backref("platform", uselist=False))

    def __init__(self, label=None, domain=None, access_token=None, owner=None, platform=None):
        self.label = label
        self.domain = domain
        self.access_token = access_token
        self.owner = owner
        self.platform = platform

    def __repr__(self):
        return '<Shop %r>' % self.id

    def serialize(self):
        return {
            'id': self.id,
            'label': self.label,
            'domain': self.domain
        }

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


class Platform(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

    def __init__(self, name=None):
        self.name = name

    @classmethod
    def get_by_name(cls, name):
        platform = cls.query.filter_by(name=name).first()
        if not platform:
            raise DbException(message='Platform %s not registered with Opinew.' % name, status_code=400)
        return platform


class ShopReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    shop = db.relationship("Shop", backref=db.backref("shop_review", uselist=False))

    review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    review = db.relationship("Review", backref=db.backref("shop_review", uselist=False))

    approved_by_shop = db.Column(db.Boolean)
    approval_pending = db.Column(db.Boolean)

    def __init__(self, shop=None, review=None):
        self.shop = shop
        self.review = review
        self.approved_by_shop = False
        self.approval_pending = True

    def serialize(self):
        return {
            'id': self.id,
            'shop': self.shop.serialize(),
            'review': self.review.serialize(),
            'approved_by_shop': self.approved_by_shop,
            'approval_pending': self.approval_pending,
        }

    @classmethod
    def get_by_shop_and_review_id(cls, shop_id, review_id):
        shop_review = cls.query.filter(and_(cls.shop_id == shop_id, cls.review_id == review_id)).first()
        if not shop_review:
            raise DbException(message='Shop %s does not have review %s' % (shop_id, review_id), status_code=400)
        return shop_review

    def approve(self):
        self.approved_by_shop = True
        self.approval_pending = False
        notification = Notification(user=self.review.user,
                                        content='The shop owner approved your review about <b>%s</b>.<br>'
                                                'View it here!' % self.review.shop_product.product.label,
                                        url=url_for('.get_product', product_id=self.review.shop_product.product.id))
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

    def __init__(self, shop=None, product=None, url=None, platform_product_id=None):
        self.shop = shop
        self.product = product
        self.url = url
        self.platform_product_id = platform_product_id

    def serialize(self):
        return {
            'id': self.id,
            'shop': self.shop.serialize(),
            'product': self.product.serialize(),
            'url': self.url
        }

    @classmethod
    def get_by_platform_product_id(cls, platform_product_id):
        sp = ShopProduct.query.filter_by(platform_product_id=platform_product_id).first()
        if not sp or not sp.product:
            raise DbException(message='Shop_Product doesn\'t exist', status_code=404)
        return sp


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String)
    tags = db.relationship("Tag", secondary=product_tags_table,
                           backref=db.backref("products", lazy="dynamic"))

    def __init__(self, label=None, **kwargs):
        self.label = label

    def __repr__(self):
        return '<Product %r>' % self.label

    def serialize_basic(self):
        return {
            'id': self.id,
            'label': self.label
        }

    def serialize(self):
        return {
            'id': self.id,
            'label': self.label,
            'tags': [t.serialize() for t in self.tags]
        }

    def serialize_with_reviews(self, reviews):
        product_serialized = self.serialize()
        product_serialized['reviews'] = [r.serialize() for r in reviews]
        return product_serialized

    def add_review(self, order, body, photo_url, tag_ids, shop_id):
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
        shop_review = ShopReview(review=review, shop=shop)
        for tag_id in tag_ids:
            tag = Tag.query.filter_by(id=tag_id).first()
            if tag:
                review.tags.append(tag)
        db.session.add(review)
        db.session.add(shop_review)
        db.session.commit()
        notification = Notification(user=shop.owner,
                                    content='You received a new review about <b>%s</b>. <br>'
                                            'Click here to allow or deny display on plugin' % review.shop_product.product.label,
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

    @classmethod
    def serialize_list(cls, products):
        return {'products': [p.serialize_basic() for p in products]}


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String)
    connotation = db.Column(db.Integer)

    def __init__(self, label=None, connotation=None, **kwargs):
        self.label = label
        self.connotation = connotation

    def __repr__(self):
        return '<Tag %r (%r)>' % (self.label, self.connotation)

    def serialize(self):
        return {
            'id': self.id,
            'connotation': self.connotation,
            'label': self.label
        }
