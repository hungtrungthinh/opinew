import csv
from webapp.models import User, UserLegacy, Review, Product, Order
from webapp.exceptions import ProductNotFoundException
from dateutil.parser import parse
from config import Constants
from webapp import db
from importer import OpinewImporter


"""
We are assuming that the shop from which the reviews came, is already registered
and we imported all of its products.
"""
class YotpoImpoter(OpinewImporter):

    def __init__(self, shop_id):
        self.shop_id = shop_id

    def csv_to_dicts_YOTPO(self, filepath):
        output =[]
        with open(filepath, 'rb') as csvfile:
            reader = csv.DictReader(csvfile, quoting=csv.QUOTE_ALL)
            for row in reader:
                if row["published"] and row["published"] == "true":
                    row_dict = {'product_title': row['product_title'],
                                'review_score': row['review_score'],
                                'review_title': row['review_title'],
                                'display_name': row['display_name'],
                                'email': row['email'],
                                'review_content': row['review_content'],
                                'date': row['date']}
                    output.append(row_dict)
        return output


    def yotpo_dict_to_Opinew_models(self, reviews):
        for row in reviews:
            #gets an instance of a user or legacy user
            user = self.create_or_match_user_from_review_data(row["display_name"], row["email"])
            self.create_review_from_yotpo_data(row["review_content"], row["product_title"],
                                                 row["review_score"], row["date"],
                                                 user)

    def create_review_from_yotpo_data(self, review_content, product_title, review_score,
                                        date, user):
        product = Product.query.filter_by(shop_id=self.shop_id,
                                             name=product_title
                                             ).first()
        product_id = None
        if not product:
            raise ProductNotFoundException
        else:
            product_id = product.id

        dt = parse(date)
        if review_score and isinstance(int(review_score), int):
            review_score = int(review_score)
        Review.create_from_import(body=review_content, image_url=None,
                                  star_rating=review_score, product_id=product_id,
                                  verified_review=None, created_ts=dt, user=user)
        # in orders check if the user that left a review about that product also ordered that product.
        # if yes, set order as notified so that we don't notify the user again
        orders = None
        if isinstance(user, User):
            orders = Order.query.filter_by(shop_id=self.shop_id, user_id=user.id).all()
        elif isinstance(user, UserLegacy):
            orders = Order.query.filter_by(shop_id=self.shop_id, user_legacy_id=user.id).all()

        if orders:
            for order in orders:
                if product in order.products:
                    order.status = Constants.ORDER_STATUS_NOTIFIED
                    db.session.add(order)
                    db.session.commit()
                    break
