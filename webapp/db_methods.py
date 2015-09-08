from flask import request
from webapp import review_photos, db
from webapp.models import User, Review, Tag

def get_reviews(product_id):
    reviews = Review.query.filter_by(product_id=product_id).order_by(Review.created_ts.desc()).all()
    return reviews

def add_product_review(order_id, user_email, product_id, payload, shop_id=None):
    body = payload.get('body', None)
    photo_url = ''
    if 'photo' in request.files:
        photo_url = review_photos.save(request.files['photo'])
    tag_ids = request.values.getlist('tag_id')
    user = User.query.filter_by(email=user_email).first()
    review = Review(order_id=order_id, user_id=user.id, product_id=product_id, shop_id=shop_id,
                    photo_url=photo_url, body=body)
    for tag_id in tag_ids:
        tag = Tag.query.filter_by(id=tag_id).first()
        if tag:
            review.tags.append(tag)
    db.session.add(review)
    db.session.commit()
    return review
