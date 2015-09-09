import json
from flask import jsonify, request, url_for
from sqlalchemy import and_
from webapp import db, auth
from webapp.api import api
from webapp.models import User, Product, Review, Shop, Order, ShopProduct
from webapp.common import get_post_payload, param_required
from webapp.db_methods import add_product_review
from webapp.exceptions import DbException, ParamException


@api.route('/products/search')
def product_search():
    try:
        query = param_required('q', request.args)
        products = Product.search_by_label(query)
    except (ParamException, DbException) as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify({'products': [p.serialize_basic() for p in products]})


@api.route('/products/<int:product_id>/reviews')
def get_product_reviews(product_id):
    try:
        product = Product.get_by_id(product_id)
        reviews = Review.get_for_product(product_id)
    except DbException as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(product.serialize_with_reviews(reviews))


@api.route('/products/<int:product_id>')
def get_product(product_id):
    try:
        product = Product.get_by_id(product_id)
    except DbException as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(product.serialize())


@api.route('/reviews/<int:review_id>')
def get_review(review_id):
    try:
        review = Review.get_by_id(review_id)
    except DbException as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(review.serialize())


##########################
# SHOP SPECIFIC API
##########################

@api.route('/shops/<int:shop_id>/products/search')
def shop_product_search(shop_id):
    try:
        query = param_required('q', request.args)
        shop_products = ShopProduct.search_for_products_in_shop(shop_id, query)
    except (ParamException, DbException) as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify({'products': [sp.product.serialize_basic() for sp in shop_products]})


@api.route('/shops/<int:shop_id>/products/<int:product_id>/reviews')
def get_shop_product_reviews(shop_id, product_id):
    try:
        product = ShopProduct.get_product_in_shop(shop_id, product_id)
        reviews = Review.get_for_product(product_id)
    except DbException as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(product.serialize_with_reviews(reviews))


@api.route('/shops/<int:shop_id>/products/<int:product_id>/reviews/approved')
def get_shop_product_reviews_approved(shop_id, product_id):
    try:
        product = ShopProduct.get_product_in_shop(shop_id, product_id)
        reviews = Review.get_approved_for_product(product_id)
    except DbException as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(product.serialize_with_reviews(reviews))


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


@api.route('/shops/<int:shop_id>/reviews/<int:review_id>', methods=['PATCH'])
@auth.login_required
def approve_shop_product_review(shop_id, review_id):
    shop_user = User.query.filter_by(email=auth.username()).first()
    if not shop_user or not shop_user.shop:
        return jsonify({"error": "User is not an owner of shop"}), 400
    if not shop_user.shop.id == shop_id:
        return jsonify({"error": "User is not an owner of this shop"}), 403
    review = Review.query.filter_by(id=review_id).first()
    if not review:
        return jsonify({"error": 'Review doesn\'t exist'}), 404
    if not review.shop == shop_user.shop:
        return jsonify({"error": 'This review is not for this shop'}), 400
    try:
        payload = get_post_payload()
    except ParamException as e:
        return jsonify({"error": e.message}), 400
    action = payload.get('action', '')
    if not action:
        return jsonify({"error": 'action param is required'}), 400
    if action == 'approve':
        review.approve()
    elif action == 'disapprove':
        review.disapprove()
    return jsonify(review.serialize())


@api.route('/shop/<int:shop_id>/orders/<int:order_id>')
@auth.login_required
def get_order(shop_id, order_id):
    shop_user = User.query.filter_by(email=auth.username()).first()
    if not shop_user or not shop_user.shop:
        return jsonify({"error": "User is not an owner of shop"}), 400
    if not shop_user.shop.id == shop_id:
        return jsonify({"error": "User is not an owner of this shop"}), 403
    order = Order.query.filter_by(id=order_id).first()
    if not order:
        return jsonify({"error": 'Order doesn\'t exist'}), 404
    if not order.shop == shop_user.shop:
        return jsonify({"error": 'This order is not for this shop'}), 400
    return jsonify(order.serialize())


@api.route('/shop/<int:shop_id>/orders', methods=['POST'])
@auth.login_required
def create_order(shop_id):
    try:
        payload = get_post_payload()
    except ParamException as e:
        return jsonify({"error": e.message}), 400
    shop_user = User.query.filter_by(email=auth.username()).first()
    if not shop_user or not shop_user.shop:
        return jsonify({"error": "User is not an owner of shop"}), 400
    if not shop_user.shop.id == shop_id:
        return jsonify({"error": "User is not an owner of this shop"}), 403

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


@api.route('/shop/<int:shop_id>/orders/<int:order_id>', methods=['PATCH'])
@auth.login_required
def update_order(shop_id, order_id):
    shop_user = User.query.filter_by(email=auth.username()).first()
    if not shop_user or not shop_user.shop:
        return jsonify({"error": "User is not an owner of shop"}), 400
    if not shop_user.shop.id == shop_id:
        return jsonify({"error": "User is not an owner of this shop"}), 403
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
