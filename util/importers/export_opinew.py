import csv
from webapp import Constants
from webapp.models import Review
from datetime import datetime

def export_reviews(shop_id):
    reviews = Review.query.filter_by(shop_id=shop_id).order_by(Review.product_id)
    with open("/" + str(shop_id)+"_" +
                str(int((datetime.now() - datetime(1970, 1, 1)).total_seconds())), 'w') as f:

        header = ["product_name", "body", "star_rating", "created_ts", "verified", "user_email", "user_name"]
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(header)
        for review in reviews:
            user_email = ""
            user_name = ""
            if review.user:
                user_email = review.user.email
                user_name = review.user.name
            elif review.user_legacy:
                user_email = review.user_legacy.email
                user_name = review.user_legacy.name

            writer.writerow([review.product.name, review.body,
                             review.star_rating, review.created_ts.strftime(Constants.OPINEW_DATE_FORMAT),
                             review.verified_review, user_email, user_name])

