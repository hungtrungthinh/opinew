from datetime import datetime
from webapp import db
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String)
    pw_hash = db.Column(db.String)

    def __init__(self, email=None, password=None, **kwargs):
        self.email = email
        self.pw_hash = generate_password_hash(password)

    @staticmethod
    def get(user_id):
        return User.query.filter_by(id=user_id).first()

    def validate_password(self, password):
        return check_password_hash(self.pw_hash, password)

    def __repr__(self):
        return '<User %r>' % self.id


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

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String)
    created_ts = db.Column(db.DateTime)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('reviews'))

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship('Product', backref=db.backref('reviews'))

    def __init__(self, user_id=None, product_id=None, body=None, **kwargs):
        self.user_id = user_id
        self.product_id = product_id
        self.body = body
        self.created_ts = datetime.utcnow()

    def __repr__(self):
        return '<Review %r>' % self.body

    def serialize(self):
        return {
            'id': self.id,
            'product': self.product.serialize(),
            'body': self.body
        }