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
class ShopifyImpoter(OpinewImporter):

    def __init__(self, shop_id):
        self.shop_id = shop_id

    def csv_to_dicts_SHOPIFY(self, filepath):
        output =[]
        with open(filepath, 'rb') as csvfile:
            reader = csv.DictReader(csvfile, quoting=csv.QUOTE_ALL)
            for row in reader:
                row_dict = {'product_handle': row['product_handle'],
                            'rating': row['rating'],
                            'title': row['title'],
                            'author': row['author'],
                            'email': row['email'],
                            'body': row['body'],
                            'created_at': row['created_at']}
                output.append(row_dict)
        return output

    def import_reviews(self, shopify_csv_filepath=None):
        shopify_reviews = self.csv_to_dicts_SHOPIFY(shopify_csv_filepath)
        for row in shopify_reviews:
            #gets an instance of a user or legacy user
            user = self.create_or_match_user_from_review_data(row["author"], row["email"])
            self.import_review_from_shopify_data(row["body"], row["product_handle"],
                                                 row["rating"], row["created_at"],
                                                 user)

    def import_review_from_shopify_data(self, body, product_handle, rating,
                                        created_at, user):
        product = Product.query.filter_by(shop_id=self.shop_id,
                                             name=product_handle
                                             ).first()
        product_id = None
        if product:
            product_id = product.id
        else:
            raise ProductNotFoundException


        if rating and isinstance(int(rating), int):
            rating = int(rating)
        dt = parse(created_at).replace(tzinfo=None)
        review = Review.create_from_import(body=body, image_url=None,
                                           star_rating=rating, product_id=product_id,
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
                    review.verified_review = True
                    db.session.add(order)
                    db.session.add(review)
                    db.session.commit()
                    break
