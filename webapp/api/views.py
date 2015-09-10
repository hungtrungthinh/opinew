from flask import jsonify, request
from webapp import auth, review_photos
from webapp.api import api
from webapp.models import User, Product, Review, Shop, Order, ShopProduct
from webapp.common import get_post_payload, param_required, build_created_response
from webapp.exceptions import DbException, ParamException


@api.route('/products/search')
def product_search():
    try:
        query = param_required('q', request.args)
        products = Product.search_by_label(query)
    except (ParamException, DbException) as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(Product.serialize_list(products))


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
        products = ShopProduct.search_for_products_in_shop(shop_id, query)
    except (ParamException, DbException) as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(Product.serialize_list(products))


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
        payload = get_post_payload()
        email = param_required('email', payload)
        password = param_required('password', payload)
        user = User.get_by_email(email)
        user.validate_password(password)
    except (ParamException, DbException) as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify({})


@api.route('/shops/<int:shop_id>/products/<int:product_id>/reviews', methods=['POST'])
@auth.login_required
def add_shop_product_review(shop_id, product_id):
    try:
        payload = get_post_payload()
        Shop.exists(shop_id)
        body = payload.get('body', None)
        photo_url = ''
        if 'photo' in request.files:
            photo_url = review_photos.save(request.files['photo'])
        tag_ids = request.values.getlist('tag_id')

        if not body and not tag_ids and not photo_url:
            raise ParamException('At least one of body, photo or tags need to be provided.', 400)

        user = User.get_by_email(auth.username())
        product = Product.get_by_id(product_id)

        order = Order.get_by_shop_product_user(shop_id, product_id, user.id)
        review = product.add_review(order=order, body=body, photo_url=photo_url, tag_ids=tag_ids)
    except (ParamException, DbException) as e:
        return jsonify({"error": e.message}), e.status_code
    return build_created_response('.get_review', review_id=review.id)


@api.route('/shops/<int:shop_id>/reviews/<int:review_id>', methods=['PATCH'])
@auth.login_required
def approve_shop_product_review(shop_id, review_id):
    try:
        shop_user = User.get_by_email(auth.username())
        shop = Shop.get_by_id(shop_id)
        shop.is_owner(shop_user)
        review = Review.get_by_id(review_id)
        review.is_for_shop(shop)

        payload = get_post_payload()
        action = param_required('action', payload)

        if action == 'approve':
            review.approve()
        elif action == 'disapprove':
            review.disapprove()
        else:
            raise ParamException('action can be one of approve|disapprove', 400)
    except (ParamException, DbException) as e:
        return jsonify({"error": e.message}), e.status_code
    return '', 204


@api.route('/shop/<int:shop_id>/orders/<int:order_id>')
@auth.login_required
def get_shop_order(shop_id, order_id):
    try:
        shop_user = User.get_by_email(auth.username())
        shop = Shop.get_by_id(shop_id)
        shop.is_owner(shop_user)
        order = Order.get_by_id(order_id)
        order.is_for_shop(shop)
    except (ParamException, DbException) as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(order.serialize())


@api.route('/shop/<int:shop_id>/orders', methods=['POST'])
@auth.login_required
def create_shop_order(shop_id):
    try:
        shop_user = User.get_by_email(auth.username())
        shop = Shop.get_by_id(shop_id)
        shop.is_owner(shop_user)

        payload = get_post_payload()
        user_email = param_required('user_email', payload)
        product_id = param_required('product_id', payload)

        user = User.get_by_email(user_email)
        product = Product.get_by_id(product_id)

        shop = shop_user.shop
        order = Order(user=user, product=product, shop=shop)
    except (ParamException, DbException) as e:
        return jsonify({"error": e.message}), e.status_code
    return build_created_response('.get_order', order_id=order.id)


@api.route('/shop/<int:shop_id>/orders/<int:order_id>', methods=['PATCH'])
@auth.login_required
def update_shop_order(shop_id, order_id):
    try:
        shop_user = User.get_by_email(auth.username())
        shop = Shop.get_by_id(shop_id)
        shop.is_owner(shop_user)

        order = Order.get_by_id(order_id)
        order.is_for_shop(shop)

        payload = get_post_payload()
        action = param_required('action', payload)

        if action == 'ship':
            order.ship()
        elif action == 'deliver':
            order.deliver()
        elif action == 'notify':
            order.notify()
        else:
            raise ParamException('action can be one of ship|deliver|notify', 400)
    except (ParamException, DbException) as e:
        return jsonify({"error": e.message}), e.status_code
    return '', 204
