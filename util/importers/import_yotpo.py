import csv
from webapp.models import User, UserLegacy, Review, Product
from webapp.exceptions import ProductNotFoundException
from dateutil.parser import parse


"""
We are assuming that the shop from which the reviews came, is already registered
and we imported all of its products.
"""
class YotpoImpoter():

    def __init__(self, shop_id):
        self.shop_id = shop_id

    def csv_to_dicts_YOTPO(self, filepath):
        output =[]
        with open('shopify_example.csv', 'rb') as csvfile:
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
            user = self.create_or_match_user_from_shopify_data(row["display_name"], row["email"])
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
        Review.create_from_import(body=review_content, image_url=None, star_rating=review_score, product_id=product_id,
                        shop_id=self.shop_id, verified_review=None, created_ts=dt, user=user)

    """
    creates a new user if his email doesn't match in the db
    """
    def create_or_match_user_from_yotpo_data(self, display_name, email):
        user = None
        existing_user = User.get_by_email_no_exception(email)
        if existing_user:
            user = existing_user
        else:
            user, is_new = UserLegacy.get_or_create_by_email(email, name=display_name)

        return user