import json
from flask import jsonify, request, url_for, abort, render_template, send_from_directory
from webapp import app, db, auth, review_photos
from models import User, Product, Review, Shop, Tag
from config import Config


def get_reviews(product_id):
    reviews = Review.query.filter_by(product_id=product_id).order_by(Review.created_ts.desc()).all()
    return reviews


def db_add_product_review(product_id, payload, shop_id=None):
    body = payload.get('body', None)
    photo_url = ''
    if 'photo' in request.files:
        photo_url = review_photos.save(request.files['photo'])
    tag_ids = request.values.getlist('tag_id')
    user = User.query.filter_by(email=auth.username()).first()
    review = Review(user_id=user.id, product_id=product_id, shop_id=shop_id, photo_url=photo_url, body=body)
    for tag_id in tag_ids:
        tag = Tag.query.filter_by(id=tag_id).first()
        if tag:
            review.tags.append(tag)
    db.session.add(review)
    db.session.commit()
    return review


@app.route('/product/search')
def product_search():
    query = request.args.get('q', None)
    if query is None:
        return jsonify({"error": 'q parameter is required'}), 400
    products = Product.query.filter(Product.label.like("%s%%" % query)).all()
    return jsonify({'products': [p.serialize_basic() for p in products]})


@app.route('/product/<int:product_id>/reviews')
def get_product_reviews(product_id):
    product = Product.query.filter_by(id=product_id).first()
    if not product:
        return jsonify({"error": 'Product doesn\'t exist'}), 404
    reviews = get_reviews(product_id)
    product_serialized = product.serialize()
    product_serialized['reviews'] = [r.serialize() for r in reviews]
    return jsonify(product_serialized)


@app.route('/plugin/product/<int:product_id>/reviews')
def get_plugin_product_reviews(product_id):
    product = Product.query.filter_by(id=product_id).first()
    if not product:
        return abort(404)
    return render_template('reviews.html', reviews=get_reviews(product_id))


@app.route('/product/<int:product_id>')
def get_product(product_id):
    product = Product.query.filter_by(id=product_id).first()
    if not product:
        return jsonify({"error": 'Product doesn\'t exist'}), 404
    return jsonify(product.serialize())


@app.route('/review/<int:review_id>')
def get_review(review_id):
    review = Review.query.filter_by(id=review_id).first()
    if not review:
        return jsonify({"error": 'Review doesn\'t exist'}), 404
    return jsonify(review.serialize())


@auth.get_password
def get_pw(username):
    user = User.query.filter_by(email=username).first()
    if user:
        return user.email
    return None


@auth.verify_password
def verify_pw(username, password):
    user = User.query.filter_by(email=username).first()
    if user:
        return user.validate_password(password)
    return False


@app.route('/authenticate', methods=['POST'])
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


@app.route('/shop/<int:shop_id>/product/<int:product_id>/reviews/add', methods=['POST'])
@auth.login_required
def add_shop_product_review(shop_id, product_id):
    if not request.form and not request.files:
        try:
            payload = json.loads(request.data)
        except ValueError:
            return jsonify({"error": "Invalid json in body of request."}), 400
    else:
        payload = request.form
    shop = Shop.query.filter_by(id=shop_id).first()
    if not shop:
        error = 'Shop %s not registered with Opinew.' % shop_id
        return jsonify({"error": error}), 400
    review = db_add_product_review(product_id, payload, shop_id)
    response = jsonify()
    response.status_code = 201
    response.headers['Location'] = url_for('get_review', review_id=review.id)
    response.autocorrect_location_header = False
    return response


@app.route('/product/<int:product_id>/reviews/add', methods=['POST'])
@auth.login_required
def add_product_review(product_id):
    if not request.form and not request.files:
        try:
            payload = json.loads(request.data)
        except ValueError:
            return jsonify({"error": "Invalid json in body of request."}), 400
    else:
        payload = request.form
    review = db_add_product_review(product_id, payload)
    response = jsonify()
    response.status_code = 201
    response.headers['Location'] = url_for('get_review', review_id=review.id)
    response.autocorrect_location_header = False
    return response


@app.route('/media/user/<path:filename>')
def media_user(filename):
    return send_from_directory(Config.UPLOADED_USERPHOTOS_DEST, filename)


@app.route('/media/review/<path:filename>')
def media_review(filename):
    return send_from_directory(Config.UPLOADED_REVIEWPHOTOS_DEST, filename)
