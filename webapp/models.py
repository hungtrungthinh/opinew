from datetime import datetime, timedelta
from sqlalchemy import and_
from webapp import db, login_manager
from webapp.common import generate_temp_password
from webapp.exceptions import DbException
from flask.ext.login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config, Constants

role_access_table = db.Table('role_access',
                             db.Column('role_id', db.Integer, db.ForeignKey('role.id')),
                             db.Column('access_id', db.Integer, db.ForeignKey('access.id'))
                             )

product_tags_table = db.Table('product_tags',
                              db.Column('product_id', db.Integer, db.ForeignKey('product.id')),
                              db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
                              )

review_tags_table = db.Table('review_tags',
                             db.Column('review_id', db.Integer, db.ForeignKey('review.id')),
                             db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
                             )


class Access(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String)

    def __init__(self, url=None, **kwargs):
        self.url = url


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    access_whitelist = db.relationship("Access", secondary=role_access_table,
                                       backref=db.backref("roles", lazy="dynamic"))

    def __init__(self, name=None, **kwargs):
        self.name = name


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String)
    temp_password = db.Column(db.String)
    pw_hash = db.Column(db.String)
    name = db.Column(db.String)
    profile_picture_url = db.Column(db.String)

    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    role = db.relationship('Role', backref=db.backref('users'))

    def __init__(self, email=None, name=None, profile_picture_url=Config.DEFAULT_PROFILE_PICTURE,
                 password=None, **kwargs):
        self.email = email
        if not password:
            self.temp_password = generate_temp_password()
            self.pw_hash = generate_password_hash(self.temp_password)
        else:
            self.pw_hash = generate_password_hash(password)
        self.name = name
        self.profile_picture_url = profile_picture_url

    @classmethod
    def get_by_id(cls, user_id):
        return cls.query.filter_by(id=user_id).first()

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

    def __repr__(self):
        return '<User %r>' % self.id

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name
        }


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    read_status = db.Column(db.Boolean)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("notifications"))

    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    order = db.relationship("Order", backref=db.backref("notifications"))

    def __init__(self, user=None, order=None):
        self.user = user
        self.order = order
        self.read_status = False


class DeliveryService(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String)
    delivery_time_in_days = db.Column(db.Integer)

    def __init__(self, label=None, delivery_time_in_days=None):
        self.label = label
        self.delivery_time_in_days = delivery_time_in_days


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=db.backref("orders"))

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship("Product", backref=db.backref("orders"))

    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    shop = db.relationship("Shop", backref=db.backref("orders"))

    review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    review = db.relationship("Review", backref=db.backref("order", uselist=False))

    delivery_service_id = db.Column(db.Integer, db.ForeignKey('delivery_service.id'))
    delivery_service = db.relationship("DeliveryService", backref=db.backref("orders"))

    delivery_tracking_number = db.Column(db.String)

    status = db.Column(db.String)  # ['PURCHASED', 'SHIPPED', 'DELIVERED', 'NOTIFIED', 'REVIEWED']

    purchase_timestamp = db.Column(db.DateTime)
    shipment_timestamp = db.Column(db.DateTime)
    delivery_timestamp = db.Column(db.DateTime)

    delivery_estimation_timestamp = db.Column(db.DateTime)
    delivery_estimation_accuracy = db.Column(db.Integer)  # points

    notification_timestamp = db.Column(db.DateTime)

    def __init__(self, user=None, product=None, shop=None, delivery_service=None):
        self.user = user
        self.product = product
        self.shop = shop

        self.status = 'PURCHASED'
        self.purchase_timestamp = datetime.utcnow()

        self.delivery_estimation_accuracy = 0
        if shop.shipment_time_in_days:
            self.delivery_estimation_timestamp = self.purchase_timestamp + \
                                                 timedelta(shop.shipment_time_in_days)

            if delivery_service:
                self.delivery_service = delivery_service
                self.delivery_estimation_accuracy += 1
                self.delivery_estimation_timestamp = self.delivery_estimation_timestamp + \
                                                     delivery_service.delivery_time_in_days

            self.notification_timestamp = self.delivery_estimation_timestamp + \
                                          timedelta(0, Constants.NOTIFICATION_AFTER_DELIVERY_SECONDS)
        db.session.add(self)
        db.session.commit()

    def is_for_shop(self, shop):
        if not self.shop == shop:
            raise DbException(message="This order is not for this shop", status_code=404)
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

    def ship(self, delivery_service=None, delivery_tracking_number=None):
        self.status = 'SHIPPED'
        self.shipment_timestamp = datetime.utcnow()
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
        notification = Notification(user=self.user, order=self)
        db.session.add(notification)
        db.session.add(self)
        db.session.commit()

    def serialize(self):
        return {
            'id': self.id,
            'user': self.user.serialize(),
            'product': self.product.serialize(),
            'shop': self.shop.serialize(),
            'review': self.review.serialize() if self.review else {},
            'status': self.status,
            'purchase_timestamp': self.purchase_timestamp,
            'shipment_timestamp': self.shipment_timestamp,
            'delivery_timestamp': self.delivery_timestamp,
            'delivery_estimation_timestamp': self.delivery_estimation_timestamp,
            'delivery_estimation_accuracy': self.delivery_estimation_accuracy,
            'notification_timestamp': self.notification_timestamp
        }


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String)
    created_ts = db.Column(db.DateTime)
    photo_url = db.Column(db.String)
    approved_by_shop = db.Column(db.Boolean)
    approval_pending = db.Column(db.Boolean)

    tags = db.relationship("Tag", secondary=review_tags_table, backref=db.backref("reviews", lazy="dynamic"))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('reviews'))

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship('Product', backref=db.backref('reviews'))

    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    shop = db.relationship('Shop', backref=db.backref('reviews'))

    def __init__(self, user_id=None, product_id=None, shop_id=None, order_id=None, body=None, photo_url=None, **kwargs):
        self.user_id = user_id
        self.product_id = product_id
        self.shop_id = shop_id
        self.order_id = order_id
        self.body = body
        self.photo_url = photo_url
        self.created_ts = datetime.utcnow()
        self.approved_by_shop = False
        self.approval_pending = True

        if self.shop:
            notification = Notification(user=self.shop.owner, order=self.order)
            db.session.add(notification)
            db.session.commit()

    def __repr__(self):
        return '<Review %r>' % self.body

    def serialize(self):
        return {
            'id': self.id,
            'body': self.body,
            'photo_url': self.photo_url,
            'approved_by_shop': self.approved_by_shop,
            'approval_pending': self.approval_pending,
            'tags': [t.serialize() for t in self.tags]
        }

    def approve(self):
        self.approved_by_shop = True
        self.approval_pending = False
        db.session.add(self)
        db.session.commit()

    def disapprove(self):
        self.approved_by_shop = False
        self.approval_pending = False
        db.session.add(self)
        db.session.commit()

    def is_for_shop(self, shop):
        if not self.order.shop == shop:
            raise DbException(message="This review is not for this shop", status_code=404)
        return True

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
    def get_for_product(cls, product_id):
        return Review.query.filter_by(product_id=product_id).order_by(Review.created_ts.desc()).all()

    @classmethod
    def get_approved_for_product(cls, product_id):
        return Review.query.filter(and_(Review.product_id == product_id, Review.approved_by_shop)).order_by(
            Review.created_ts.desc()).all()


class Shop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String)
    url = db.Column(db.String)
    shipment_time_in_days = db.Column(db.Integer)

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship("User", backref=db.backref("shop", uselist=False))

    def __init__(self, label=None, url=None, owner=None, shipment_time_in_days=None):
        self.label = label
        self.url = url
        self.owner = owner
        self.shipment_time_in_days = shipment_time_in_days

    def __repr__(self):
        return '<Shop %r>' % self.id

    def serialize(self):
        return {
            'id': self.id,
            'label': self.label
        }

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


class ShopProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String)

    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    shop = db.relationship("Shop", backref=db.backref("shop_product", uselist=False))

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship("Product", backref=db.backref("shop_product", uselist=False))

    def __init__(self, shop=None, product=None, url=None):
        self.shop = shop
        self.product = product
        self.url = url

    def serialize(self):
        return {
            'id': self.id,
            'shop': self.shop.serialize(),
            'product': self.product.serialize(),
            'url': self.url
        }

    @classmethod
    def search_for_products_in_shop(cls, shop_id, query):
        try:
            Shop.exists(shop_id)
        except:
            raise
        shop_products = cls.query.filter(and_(ShopProduct.shop_id == shop_id, Product.label.like("%s%%" % query))).all()
        return [sp.product for sp in shop_products]

    @classmethod
    def get_product_in_shop(cls, shop_id, product_id):
        try:
            Shop.exists(shop_id)
        except:
            raise
        sp = ShopProduct.query.filter(
            and_(ShopProduct.shop_id == shop_id, ShopProduct.product_id == product_id)).first()
        if not sp or not sp.product:
            raise DbException(message='Product doesn\'t exist', status_code=404)
        return sp.product


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String)
    tags = db.relationship("Tag", secondary=product_tags_table, backref=db.backref("products", lazy="dynamic"))

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

    def add_review(self, order, body, photo_url, tag_ids):
        user = User.get_by_email(order.user.email)
        review = Review(order_id=order.id, user_id=user.id, product_id=self.id, shop_id=order.shop.id,
                        photo_url=photo_url, body=body)
        for tag_id in tag_ids:
            tag = Tag.query.filter_by(id=tag_id).first()
            if tag:
                review.tags.append(tag)
        db.session.add(review)
        db.session.commit()
        return review

    @classmethod
    def get_by_id(cls, product_id):
        product = cls.query.filter(Product.id == product_id).first()
        if not product:
            raise DbException(message='Product doesn\'t exist', status_code=404)
        return product

    @classmethod
    def search_by_label(cls, query):
        return Product.query.filter(Product.label.like("%s%%" % query)).all()

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
