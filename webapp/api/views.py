import json
from flask import jsonify, request, url_for
from sqlalchemy import and_
from webapp import db, auth
from webapp.api import api
from webapp.models import User, Product, Review, Shop, Order
from webapp.common import get_post_payload
from webapp.db_methods import get_reviews, add_product_review
from webapp.exceptions import ParamException


@api.route('/products/search')
def product_search():
    query = request.args.get('q', None)
    if query is None:
        return jsonify({"error": 'q parameter is required'}), 400
    products = Product.query.filter(Product.label.like("%s%%" % query)).all()
    return jsonify({'products': [p.serialize_basic() for p in products]})


@api.route('/products/<int:product_id>/reviews')
def get_product_reviews(product_id):
    product = Product.query.filter(Product.id == product_id).first()
    if not product:
        return jsonify({"error": 'Product doesn\'t exist'}), 404
    reviews = get_reviews(product_id)
    product_serialized = product.serialize()
    product_serialized['reviews'] = [r.serialize() for r in reviews]
    return jsonify(product_serialized)


@api.route('/products/<int:product_id>')
def get_product(product_id):
    product = Product.query.filter_by(id=product_id).first()
    if not product:
        return jsonify({"error": 'Product doesn\'t exist'}), 404
    return jsonify(product.serialize())


@api.route('/reviews/<int:review_id>')
def get_review(review_id):
    review = Review.query.filter_by(id=review_id).first()
    if not review:
        return jsonify({"error": 'Review doesn\'t exist'}), 404
    return jsonify(review.serialize())


##########################
# SHOP SPECIFIC API
##########################

@api.route('/shops/<int:shop_id>/products/search')
def shop_product_search(shop_id):
    shop = Shop.query.filter_by(id=shop_id).first()
    if not shop:
        error = 'Shop %s not registered with Opinew.' % shop_id
        return jsonify({"error": error}), 400
    query = request.args.get('q', None)
    if query is None:
        return jsonify({"error": 'q parameter is required'}), 400
    products = Product.query.filter(and_(Product.shop == shop, Product.label.like("%s%%" % query))).all()
    return jsonify({'products': [p.serialize_basic() for p in products]})


@api.route('/shops/<int:shop_id>/products/<int:product_id>/reviews')
def get_shop_product_reviews(shop_id, product_id):
    shop = Shop.query.filter_by(id=shop_id).first()
    if not shop:
        error = 'Shop %s not registered with Opinew.' % shop_id
        return jsonify({"error": error}), 400
    product = Product.query.filter(and_(Product.shop == shop, Product.id == product_id)).first()
    if not product:
        return jsonify({"error": 'Product doesn\'t exist'}), 404
    reviews = get_reviews(product_id)
    product_serialized = product.serialize()
    product_serialized['reviews'] = [r.serialize() for r in reviews]
    return jsonify(product_serialized)


##########################
# AUTHENTICATION API
##########################

@api.route('/authenticate', methods=['POST'])
def authenticate():
    try:
        payload = json.loads(request.data)
    except ValueError:
        return jsonify({"error": "Invalid json in body of request."}), 400
    email = payload.get('email')
    password = payload.get('password')
    if not (email and password):
        return jsonify({"error": "Email and password pair is required."}), 400
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "User with email %s does not exist." % email}), 400
    if not user.validate_password(password):
        return jsonify({"error": "Wrong password for user %s." % email}), 400
    return jsonify({})


@api.route('/shops/<int:shop_id>/products/<int:product_id>/reviews', methods=['POST'])
@auth.login_required
def add_shop_product_review(shop_id, product_id):
    try:
        payload = get_post_payload()
    except ParamException as e:
        return jsonify({"error": e.message}), 400
    shop = Shop.query.filter_by(id=shop_id).first()
    if not shop:
        error = 'Shop %s not registered with Opinew.' % shop_id
        return jsonify({"error": error}), 400
    user = User.query.filter_by(email=auth.username()).first()
    order_id = 0
    if user:
        order = Order.query.filter(and_(Order.shop_id == shop_id,
                                        Order.product_id == product_id,
                                        Order.user_id == user.id)).first()
        if order:
            order_id = order.id
    review = add_product_review(order_id=order_id, user_email=auth.username(), product_id=product_id, payload=payload,
                                shop_id=shop_id)
    response = jsonify()
    response.status_code = 201
    response.headers['Location'] = url_for('.get_review', review_id=review.id)
    response.autocorrect_location_header = False
    return response


@api.route('/orders/<int:order_id>')
@auth.login_required
def get_order(order_id):
    shop_user = User.query.filter_by(email=auth.username()).first()
    if not shop_user or not shop_user.shop:
        return jsonify({"error": "User is not an owner of shop"}), 400
    order = Order.query.filter_by(id=order_id).first()
    if not order:
        return jsonify({"error": 'Order doesn\'t exist'}), 404
    if not order.shop == shop_user.shop:
        return jsonify({"error": 'This order is not for this shop'}), 400
    return jsonify(order.serialize())


@api.route('/orders', methods=['POST'])
@auth.login_required
def create_order():
    try:
        payload = get_post_payload()
    except ParamException as e:
        return jsonify({"error": e.message}), 400
    shop_user = User.query.filter_by(email=auth.username()).first()
    if not shop_user or not shop_user.shop:
        return jsonify({"error": "User is not an owner of shop"}), 400

    user_email = payload.get('user_email')
    product_id = payload.get('product_id')

    user = User.query.filter_by(email=user_email).first()
    product = Product.query.filter_by(id=product_id).first()
    shop = shop_user.shop

    if not product or not shop:
        return jsonify({"error": 'non existing'}), 400

    if not user:
        user = User(email=user_email)
        db.session.add(user)

    order = Order(user=user, product=product, shop=shop)
    db.session.add(order)
    db.session.commit()

    response = jsonify()
    response.status_code = 201
    response.headers['Location'] = url_for('.get_order', order_id=order.id)
    response.autocorrect_location_header = False
    return response


@api.route('/orders/<int:order_id>', methods=['PATCH'])
@auth.login_required
def update_order(order_id):
    shop_user = User.query.filter_by(email=auth.username()).first()
    if not shop_user or not shop_user.shop:
        return jsonify({"error": "User is not an owner of shop"}), 400
    order = Order.query.filter_by(id=order_id).first()
    if not order:
        return jsonify({"error": 'Order doesn\'t exist'}), 404
    if not order.shop == shop_user.shop:
        return jsonify({"error": 'This order is not for this shop'}), 400
    try:
        payload = get_post_payload()
    except ParamException as e:
        return jsonify({"error": e.message}), 400
    action = payload.get('action', '')
    if not action:
        return jsonify({"error": 'action param is required'}), 400
    if action == 'ship':
        order.ship()
    elif action == 'deliver':
        order.deliver()
    elif action == 'notify':
        order.notify()
    return jsonify(order.serialize())
