from datetime import datetime
from webapp import db, review_photos
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String)
    pw_hash = db.Column(db.String)
    name = db.Column(db.String)
    profile_picture_url = db.Column(db.String)

    def __init__(self, email=None, name=None, profile_picture_url=Config.DEFAULT_PROFILE_PICTURE,
                 password=None, **kwargs):
        self.email = email
        self.pw_hash = generate_password_hash(password)
        self.name = name
        self.profile_picture_url = profile_picture_url

    @staticmethod
    def get(user_id):
        return User.query.filter_by(id=user_id).first()

    def validate_password(self, password):
        return check_password_hash(self.pw_hash, password)

    def __repr__(self):
        return '<User %r>' % self.id


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String)
    created_ts = db.Column(db.DateTime)
    photo_url = db.Column(db.String)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('reviews'))

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship('Product', backref=db.backref('reviews'))

    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    shop = db.relationship('Shop', backref=db.backref('reviews'))

    def __init__(self, user_id=None, product_id=None, shop_id=None, body=None, photo_url=None, **kwargs):
        self.user_id = user_id
        self.product_id = product_id
        self.shop_id = shop_id
        self.body = body
        self.photo_url = photo_url
        self.created_ts = datetime.utcnow()

    def __repr__(self):
        return '<Review %r>' % self.body

    def serialize(self):
        return {
            'id': self.id,
            'body': self.body,
            'photo_url': self.photo_url
        }


shop_products_table = db.Table('shop_products',
                               db.Column('shop_id', db.Integer, db.ForeignKey('shop.id')),
                               db.Column('product_id', db.Integer, db.ForeignKey('product.id'))
                               )


class Shop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    products = db.relationship("Product", secondary=shop_products_table, backref=db.backref("shops", lazy="dynamic"))

    def __repr__(self):
        return '<Shop %r>' % self.id

    def serialize(self):
        return {
            'id': self.id,
            'label': self.label
        }


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String)

    def __init__(self, label=None, **kwargs):
        self.label = label

    def __repr__(self):
        return '<Product %r>' % self.label

    def serialize(self):
        return {
            'id': self.id,
            'label': self.label
        }
