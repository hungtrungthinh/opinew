from flask import jsonify, request, url_for, abort, render_template, send_from_directory
from webapp import app, db, auth, review_photos
from models import User, Product, Review, Shop
from config import Config


def get_reviews(product_id):
    reviews = Review.query.filter_by(product_id=product_id).order_by(Review.created_ts.desc()).all()
    return reviews


@app.route('/product/<int:product_id>/reviews')
def get_product_reviews(product_id):
    product = Product.query.filter_by(id=product_id).first()
    if not product:
        return jsonify({"ERROR": 'Product doesn\'t exist'}), 404
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
        return jsonify({"ERROR": 'Product doesn\'t exist'}), 404
    return jsonify(product.serialize())


@app.route('/review/<int:review_id>')
def get_review(review_id):
    review = Review.query.filter_by(id=review_id).first()
    if not review:
        return jsonify({"ERROR": 'Review doesn\'t exist'}), 404
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


@app.route('/product/<int:product_id>/reviews/add', methods=['POST'])
@auth.login_required
def add_product_review(product_id):
    shop_id = request.form.get('shop_id', None)
    if not shop_id:
        error = 'Review shop_id required.'
        return jsonify({"ERROR": error}), 400
    shop = Shop.query.filter_by(id=shop_id).first()
    if not shop:
        error = 'Shop %s not registered with Opinew.' % shop_id
        return jsonify({"ERROR": error}), 400
    body = request.form.get('body', None)
    if not body:
        error = 'Review body required.'
        return jsonify({"ERROR": error}), 400
    photo_url = ''
    if 'review_picture' in request.files:
        photo_url = review_photos.save(request.files['review_picture'])
    user = User.query.filter_by(email=auth.username()).first()
    review = Review(user_id=user.id, product_id=product_id, shop_id=shop_id, photo_url=photo_url,
                    body=body)
    db.session.add(review)
    db.session.commit()
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
