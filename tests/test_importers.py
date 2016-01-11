from framework import TestImporters
import testing_constants
import os
from webapp.models import User, UserLegacy
from webapp import db


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
        reviews = self.shopify_importer.csv_to_dicts_SHOPIFY(os.path.join(self.basedir, 'test_files', 'shopify_example.csv'))
        self.assertTrue(reviews is not None)
        self.assertTrue(len(reviews) > 0)
        self.assertTrue(len(reviews) > 1)
        self.assertTrue(cmp(expected_dict, reviews[0]) == 0)

    def test_shopify_import_get_or_create_legacy_user_doesnt_exist(self):
        self.refresh_db()
        reviews = self.shopify_importer.csv_to_dicts_SHOPIFY(os.path.join(self.basedir, 'test_files', 'shopify_example.csv'))
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
        reviews = self.shopify_importer.csv_to_dicts_SHOPIFY(os.path.join(self.basedir, 'test_files', 'shopify_example.csv'))
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
        reviews = self.shopify_importer.csv_to_dicts_SHOPIFY(os.path.join(self.basedir, 'test_files', 'shopify_example.csv'))
        review_row_1 = reviews[0]
        user = self.shopify_importer.create_or_match_user_from_review_data(review_row_1["author"],
                                                                            review_row_1["email"])
        self.assertTrue(isinstance(user, User))
        self.assertEqual(user.email, testing_constants.ORDER_USER_EMAIL)
        self.assertEqual(user.name, testing_constants.ORDER_USER_NAME)
        self.assertEqual(len(User.query.filter_by(email=testing_constants.ORDER_USER_EMAIL).all()), 1)
        
    
    #######YOTPO#######
    
    def test_YOTPO_import_convert_csv_to_dict(self):
        expected_dict = {'product_title': testing_constants.NEW_PRODUCT_NAME,
                        'review_score': "4",
                        'review_title': "This is an example of a review title",
                        'display_name': testing_constants.ORDER_USER_NAME,
                        'email': testing_constants.ORDER_USER_EMAIL,
                        'review_content': testing_constants.NEW_REVIEW_BODY,
                        'date': testing_constants.YOTPO_REVIEW_TIMESTAMP}
        reviews = self.yotpo_importer.csv_to_dicts_YOTPO(os.path.join(self.basedir, 'test_files', 'yotpo_example.csv'))
        self.assertTrue(reviews is not None)
        self.assertTrue(len(reviews) > 0)
        self.assertTrue(len(reviews) > 1)
        self.assertTrue(cmp(expected_dict, reviews[0]) == 0)

    def test_YOTPO_import_get_or_create_legacy_user_doesnt_exist(self):
        self.refresh_db()
        reviews = self.yotpo_importer.csv_to_dicts_YOTPO(os.path.join(self.basedir, 'test_files', 'yotpo_example.csv'))
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
        reviews = self.yotpo_importer.csv_to_dicts_YOTPO(os.path.join(self.basedir, 'test_files', 'yotpo_example.csv'))
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
        reviews = self.yotpo_importer.csv_to_dicts_YOTPO(os.path.join(self.basedir, 'test_files', 'yotpo_example.csv'))
        review_row_1 = reviews[0]
        user = self.shopify_importer.create_or_match_user_from_review_data(review_row_1["display_name"],
                                                                            review_row_1["email"])
        self.assertTrue(isinstance(user, User))
        self.assertEqual(user.email, testing_constants.ORDER_USER_EMAIL)
        self.assertEqual(user.name, testing_constants.ORDER_USER_NAME)
        self.assertEqual(len(User.query.filter_by(email=testing_constants.ORDER_USER_EMAIL).all()), 1)


