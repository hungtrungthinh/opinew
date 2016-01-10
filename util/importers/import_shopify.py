import csv
from webapp.models import User, UserLegacy, Review, Product
from webapp.exceptions import ProductNotFoundException
from dateutil.parser import parse


"""
We are assuming that the shop from which the reviews came, is already registered
and we imported all of its products.
"""
class ShopifyImpoter():

    def __init__(self, shop_id):
        self.shop_id = shop_id

    def csv_to_dicts_SHOPIFY(self, filepath=None):
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

    def shopify_dict_to_Opinew_models(self, reviews):
        for row in reviews:
            #gets an instance of a user or legacy user
            user = self.create_or_match_user_from_shopify_data(row["author"], row["email"])
            self.create_review_from_shopify_data(row["body"], row["product_handle"],
                                                 row["rating"], row["created_at"],
                                                 user)

    def create_review_from_shopify_data(self, body, product_handle, rating,
                                        created_at, user):
        product = Product.query.filter_by(shop_id=self.shop_id,
                                             name=product_handle
                                             ).first()
        product_id = None
        if not product:
            raise ProductNotFoundException
        else:
            product_id = product.id

        if rating and isinstance(int(rating), int):
            rating = int(rating)
        dt = parse(created_at)
        review = Review.create_from_import(body=body, image_url=None,
                                           star_rating=rating, product_id=product_id,
                                           verified_review=None, created_ts=dt, user=user)

        return review

    """
    creates a new user if his email doesn't match in the db
    """
    def create_or_match_user_from_shopify_data(self, author=None, email=None):
        user = None
        existing_user = User.get_by_email_no_exception(email)
        if existing_user:
            user = existing_user
        else:
            user, is_new = UserLegacy.get_or_create_by_email(email, name=author)


        return user