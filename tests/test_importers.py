from framework import TestImporters
import testing_constants
import os
from webapp.models import User, UserLegacy, Review, Product, Order
from webapp import db
from webapp.exceptions import ProductNotFoundException
from dateutil.parser import parse
from webapp import Constants


class TestModel(TestImporters):

    ######SHOPIFY#########
    def test_shopify_import_convert_csv_to_dict(self):
        expected_dict = {'product_handle': testing_constants.NEW_PRODUCT_NAME,
                        'rating': "4",
                        'title': "This is an example of a review title",
                        'author': testing_constants.ORDER_USER_NAME,
                        'email': testing_constants.ORDER_USER_EMAIL,
                        'body': testing_constants.NEW_REVIEW_BODY,
                        'created_at': testing_constants.SHOPIFY_REVIEW_TIMESTAMP}
        reviews = self.shopify_importer.csv_to_dicts_SHOPIFY(testing_constants.SHOPIFY_REVIEWS_CSV_FILEPATH)
        self.assertTrue(reviews is not None)
        self.assertTrue(len(reviews) > 0)
        self.assertTrue(len(reviews) > 1)
        self.assertTrue(cmp(expected_dict, reviews[0]) == 0)

    def test_shopify_import_get_or_create_legacy_user_doesnt_exist(self):
        self.refresh_db()
        reviews = self.shopify_importer.csv_to_dicts_SHOPIFY(testing_constants.SHOPIFY_REVIEWS_CSV_FILEPATH)
        review_row_1 = reviews[0]
        user = self.shopify_importer.create_or_match_user_from_review_data(review_row_1["author"],
                                                                            review_row_1["email"])
        self.assertTrue(isinstance(user, UserLegacy))
        self.assertEqual(user.email, testing_constants.ORDER_USER_EMAIL)
        self.assertEqual(user.name, testing_constants.ORDER_USER_NAME)
        self.assertEqual(len(UserLegacy.query.filter_by(email=testing_constants.ORDER_USER_EMAIL).all()), 1)

    def test_shopify_import_get_or_create_legacy_user_exists(self):
        self.refresh_db()
        user_legacy = UserLegacy(name=testing_constants.ORDER_USER_NAME, email=testing_constants.ORDER_USER_EMAIL)
        db.session.add(user_legacy)
        db.session.commit()
        reviews = self.shopify_importer.csv_to_dicts_SHOPIFY(testing_constants.SHOPIFY_REVIEWS_CSV_FILEPATH)
        review_row_1 = reviews[0]
        user = self.shopify_importer.create_or_match_user_from_review_data(review_row_1["author"],
                                                                            review_row_1["email"])
        self.assertTrue(isinstance(user, UserLegacy))
        self.assertEqual(user.email, testing_constants.ORDER_USER_EMAIL)
        self.assertEqual(user.name, testing_constants.ORDER_USER_NAME)
        self.assertEqual(len(UserLegacy.query.filter_by(email=testing_constants.ORDER_USER_EMAIL).all()), 1)

    def test_shopify_import_get_normal_user(self):
        self.refresh_db()
        existing_user = User(email=testing_constants.ORDER_USER_EMAIL, name=testing_constants.ORDER_USER_NAME)
        db.session.add(existing_user)
        db.session.commit()
        reviews = self.shopify_importer.csv_to_dicts_SHOPIFY(testing_constants.SHOPIFY_REVIEWS_CSV_FILEPATH)
        review_row_1 = reviews[0]
        user = self.shopify_importer.create_or_match_user_from_review_data(review_row_1["author"],
                                                                            review_row_1["email"])
        self.assertTrue(isinstance(user, User))
        self.assertEqual(user.email, testing_constants.ORDER_USER_EMAIL)
        self.assertEqual(user.name, testing_constants.ORDER_USER_NAME)
        self.assertEqual(len(User.query.filter_by(email=testing_constants.ORDER_USER_EMAIL).all()), 1)

    def test_shopify_import_reviews_products_not_imported(self):
        self.refresh_db()
        imported = self.shopify_importer.import_reviews(testing_constants.SHOPIFY_REVIEWS_CSV_FILEPATH)
        self.assertEqual(imported["num_of_reviews"], 3)
        self.assertEqual(imported["num_imported"], 0)

    def test_SHOPIFY_import_reviews(self):
        self.refresh_db()
        p = Product(shop_id=self.shopify_shop.id, name=testing_constants.NEW_PRODUCT_NAME)
        db.session.add(p)
        db.session.commit()
        before_count = len(Review.query.all())
        self.shopify_importer.import_reviews(testing_constants.SHOPIFY_REVIEWS_CSV_FILEPATH)
        after_count = len(Review.query.all())
        u = UserLegacy.query.filter_by(email=testing_constants.ORDER_USER_EMAIL).first()
        r = Review.query.filter_by(user_legacy=u).first()
        self.assertEqual(after_count, before_count+3)
        self.assertNotEqual(r, None)
        self.assertEqual(r.body, testing_constants.NEW_REVIEW_BODY)
        self.assertEqual(r.product, p)
        self.assertEqual(r.star_rating, 4)
        self.assertEqual(r.created_ts, parse(testing_constants.SHOPIFY_REVIEW_TIMESTAMP).replace(tzinfo=None))
        self.assertEqual(r.youtube_video, None)
        self.assertFalse(r.verified_review)

    def test_shopify_import_reviews_verified_review(self):
        self.refresh_db()
        p = Product(shop_id=self.shopify_shop.id, name=testing_constants.NEW_PRODUCT_NAME)
        user_legacy = UserLegacy(name=testing_constants.ORDER_USER_NAME, email=testing_constants.ORDER_USER_EMAIL)
        o = Order(user_legacy=user_legacy, shop=self.shopify_shop, status=Constants.ORDER_STATUS_NOTIFIED)
        o.products.append(p)
        db.session.add(p)
        db.session.add(o)
        db.session.commit()
        before_count = len(Review.query.all())
        self.shopify_importer.import_reviews(testing_constants.SHOPIFY_REVIEWS_CSV_FILEPATH)
        after_count = len(Review.query.all())
        r = Review.query.filter_by(user_legacy=user_legacy).first()
        self.assertEqual(after_count, before_count+3)
        self.assertNotEqual(r, None)
        self.assertEqual(r.body, testing_constants.NEW_REVIEW_BODY)
        self.assertEqual(r.product, p)
        self.assertEqual(r.star_rating, 4)
        self.assertEqual(r.created_ts, parse(testing_constants.SHOPIFY_REVIEW_TIMESTAMP).replace(tzinfo=None))
        self.assertEqual(r.youtube_video, None)
        self.assertTrue(r.verified_review)

    def test_shopify_import_reviews_ordered_verified_review_2(self):
        self.refresh_db()
        p = Product(shop_id=self.shopify_shop.id, name=testing_constants.NEW_PRODUCT_NAME)
        user_legacy = UserLegacy(name=testing_constants.ORDER_USER_NAME, email=testing_constants.ORDER_USER_EMAIL)
        o = Order(user_legacy=user_legacy, shop=self.shopify_shop)
        o.products.append(p)
        db.session.add(p)
        db.session.add(o)
        db.session.commit()
        before_count = len(Review.query.all())
        self.shopify_importer.import_reviews(testing_constants.SHOPIFY_REVIEWS_CSV_FILEPATH)
        after_count = len(Review.query.all())
        r = Review.query.filter_by(user_legacy=user_legacy).first()
        self.assertEqual(after_count, before_count+3)
        self.assertNotEqual(r, None)
        self.assertEqual(r.body, testing_constants.NEW_REVIEW_BODY)
        self.assertEqual(r.product, p)
        self.assertEqual(r.star_rating, 4)
        self.assertEqual(r.created_ts, parse(testing_constants.SHOPIFY_REVIEW_TIMESTAMP).replace(tzinfo=None))
        self.assertEqual(r.youtube_video, None)
        self.assertTrue(r.verified_review)
    
    #######YOTPO#######
    
    def test_YOTPO_import_convert_csv_to_dict(self):
        expected_dict = {'product_title': testing_constants.NEW_PRODUCT_NAME,
                        'review_score': "4",
                        'review_title': "This is an example of a review title",
                        'display_name': testing_constants.ORDER_USER_NAME,
                        'email': testing_constants.ORDER_USER_EMAIL,
                        'review_content': testing_constants.NEW_REVIEW_BODY,
                        'date': testing_constants.YOTPO_REVIEW_TIMESTAMP}
        reviews = self.yotpo_importer.csv_to_dicts_YOTPO(testing_constants.YOTPO_REVIEWS_CSV_FILEPATH)
        self.assertTrue(reviews is not None)
        self.assertTrue(len(reviews) > 0)
        self.assertTrue(len(reviews) > 1)
        self.assertTrue(cmp(expected_dict, reviews[0]) == 0)

    def test_YOTPO_import_get_or_create_legacy_user_doesnt_exist(self):
        self.refresh_db()
        reviews = self.yotpo_importer.csv_to_dicts_YOTPO(testing_constants.YOTPO_REVIEWS_CSV_FILEPATH)
        review_row_1 = reviews[0]
        user = self.yotpo_importer.create_or_match_user_from_review_data(review_row_1["display_name"],
                                                                            review_row_1["email"])
        self.assertTrue(isinstance(user, UserLegacy))
        self.assertEqual(user.email, testing_constants.ORDER_USER_EMAIL)
        self.assertEqual(user.name, testing_constants.ORDER_USER_NAME)
        self.assertEqual(len(UserLegacy.query.filter_by(email=testing_constants.ORDER_USER_EMAIL).all()), 1)

    def test_YOTPO_import_get_or_create_legacy_user_exists(self):
        self.refresh_db()
        user_legacy = UserLegacy(name=testing_constants.ORDER_USER_NAME, email=testing_constants.ORDER_USER_EMAIL)
        db.session.add(user_legacy)
        db.session.commit()
        reviews = self.yotpo_importer.csv_to_dicts_YOTPO(testing_constants.YOTPO_REVIEWS_CSV_FILEPATH)
        review_row_1 = reviews[0]
        user = self.shopify_importer.create_or_match_user_from_review_data(review_row_1["display_name"],
                                                                            review_row_1["email"])
        self.assertTrue(isinstance(user, UserLegacy))
        self.assertEqual(user.email, testing_constants.ORDER_USER_EMAIL)
        self.assertEqual(user.name, testing_constants.ORDER_USER_NAME)
        self.assertEqual(len(UserLegacy.query.filter_by(email=testing_constants.ORDER_USER_EMAIL).all()), 1)

    def test_YOTPO_import_get_normal_user(self):
        self.refresh_db()
        existing_user = User(email=testing_constants.ORDER_USER_EMAIL, name=testing_constants.ORDER_USER_NAME)
        db.session.add(existing_user)
        db.session.commit()
        reviews = self.yotpo_importer.csv_to_dicts_YOTPO(testing_constants.YOTPO_REVIEWS_CSV_FILEPATH)
        review_row_1 = reviews[0]
        user = self.shopify_importer.create_or_match_user_from_review_data(review_row_1["display_name"],
                                                                            review_row_1["email"])
        self.assertTrue(isinstance(user, User))
        self.assertEqual(user.email, testing_constants.ORDER_USER_EMAIL)
        self.assertEqual(user.name, testing_constants.ORDER_USER_NAME)
        self.assertEqual(len(User.query.filter_by(email=testing_constants.ORDER_USER_EMAIL).all()), 1)

    def test_YOTPO_import_reviews_products_not_imported(self):
        self.refresh_db()
        imported = self.yotpo_importer.import_reviews(testing_constants.YOTPO_REVIEWS_CSV_FILEPATH)
        self.assertEqual(imported["num_of_reviews"], 2)
        self.assertEqual(imported["num_imported"], 0)

    def test_YOTPO_import_reviews_products_deleted_after_review_posted(self):
        self.refresh_db()
        imported = self.yotpo_importer.import_reviews(testing_constants.YOTPO_REVIEWS_CSV_FILEPATH)
        self.assertEqual(imported["num_of_reviews"], 2)
        self.assertEqual(imported["num_imported"], 0)

    def test_YOTPO_import_reviews(self):
        self.refresh_db()
        p = Product(shop_id=self.yotpo_shop.id, name=testing_constants.NEW_PRODUCT_NAME)
        db.session.add(p)
        db.session.commit()
        before_count = len(Review.query.all())
        self.yotpo_importer.import_reviews(testing_constants.YOTPO_REVIEWS_CSV_FILEPATH)
        after_count = len(Review.query.all())
        u = UserLegacy.query.filter_by(email=testing_constants.ORDER_USER_EMAIL).first()
        r = Review.query.filter_by(user_legacy=u).first()
        self.assertEqual(after_count, before_count+2)
        self.assertNotEqual(r, None)
        self.assertEqual(r.body, testing_constants.NEW_REVIEW_BODY)
        self.assertEqual(r.product, p)
        self.assertEqual(r.star_rating, 4)
        self.assertEqual(r.created_ts, parse(testing_constants.YOTPO_REVIEW_TIMESTAMP).replace(tzinfo=None))
        self.assertEqual(r.youtube_video, None)
        self.assertFalse(r.verified_review)

    def test_YOTPO_import_reviews_verified_review(self):
        self.refresh_db()
        p = Product(shop_id=self.yotpo_shop.id, name=testing_constants.NEW_PRODUCT_NAME)
        user_legacy = UserLegacy(name=testing_constants.ORDER_USER_NAME, email=testing_constants.ORDER_USER_EMAIL)
        o = Order(user_legacy=user_legacy, shop=self.yotpo_shop, status=Constants.ORDER_STATUS_NOTIFIED)
        o.products.append(p)
        db.session.add(p)
        db.session.add(o)
        db.session.commit()
        before_count = len(Review.query.all())
        self.yotpo_importer.import_reviews(testing_constants.YOTPO_REVIEWS_CSV_FILEPATH)
        after_count = len(Review.query.all())
        r = Review.query.filter_by(user_legacy=user_legacy).first()
        self.assertEqual(after_count, before_count+2)
        self.assertNotEqual(r, None)
        self.assertEqual(r.body, testing_constants.NEW_REVIEW_BODY)
        self.assertEqual(r.product, p)
        self.assertEqual(r.star_rating, 4)
        self.assertEqual(r.created_ts, parse(testing_constants.YOTPO_REVIEW_TIMESTAMP).replace(tzinfo=None))
        self.assertEqual(r.youtube_video, None)
        self.assertTrue(r.verified_review)
