from flask import jsonify, request, url_for
from webapp import app, db, auth
from models import User, Product, Review


@app.route('/product/<int:product_id>/reviews')
def get_product_reviews(product_id):
    product = Product.query.filter_by(id=product_id).first()
    if not product:
        return jsonify({"ERROR": 'Product doesn\'t exist'}), 404
    product_serialized = product.serialize()
    product_serialized['reviews'] = [r.serialize() for r in product.reviews]
    return jsonify(product_serialized)


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
    body = request.form.get('body', None)
    if not body:
        error = 'Review body required.'
        return jsonify({"ERROR": error}), 400
    user = User.query.filter_by(email=auth.username()).first()
    review = Review(user_id=user.id, product_id=product_id, body=body)
    db.session.add(review)
    db.session.commit()
    response = jsonify()
    response.status_code = 201
    response.headers['Location'] = url_for('get_review', review_id=review.id)
    response.autocorrect_location_header = False
    return response
