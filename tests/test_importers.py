from framework import TestImporters
import testing_constants
import os
from webapp.models import User, UserLegacy
from webapp import db


class TestModel(TestImporters):

    def test_shopify_import(self):
        expected_dict = {'product_handle': testing_constants.NEW_PRODUCT_NAME,
                        'rating': "4",
                        'title': "This is an example of a review title",
                        'author': "John Appleseed",
                        'email': "john.appleseed@example.com",
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
        user = self.shopify_importer.create_or_match_user_from_shopify_data(author=review_row_1["author"],
                                                                            email=review_row_1["email"])
        self.assertTrue(isinstance(user, UserLegacy))
        self.assertEqual(user.email, "john.appleseed@example.com")
        self.assertEqual(user.name, "John Appleseed")
        self.assertEqual(len(UserLegacy.query.filter_by(email="john.appleseed@example.com").all()), 1)

    def test_shopify_import_get_or_create_legacy_user_exists(self):
        self.refresh_db()
        user_legacy = UserLegacy(name="John Appleseed", email="john.appleseed@example.com")
        db.session.add(user_legacy)
        db.session.commit()
        reviews = self.shopify_importer.csv_to_dicts_SHOPIFY(os.path.join(self.basedir, 'test_files', 'shopify_example.csv'))
        review_row_1 = reviews[0]
        user = self.shopify_importer.create_or_match_user_from_shopify_data(author=review_row_1["author"],
                                                                            email=review_row_1["email"])
        self.assertTrue(isinstance(user, UserLegacy))
        self.assertEqual(user.email, "john.appleseed@example.com")
        self.assertEqual(user.name, "John Appleseed")
        self.assertEqual(len(UserLegacy.query.filter_by(email="john.appleseed@example.com").all()), 1)

    def test_shopify_import_get_normal_user(self):
        self.refresh_db()
        existing_user = User(email="john.appleseed@example.com", name="John Appleseed")
        db.session.add(existing_user)
        db.session.commit()
        reviews = self.shopify_importer.csv_to_dicts_SHOPIFY(os.path.join(self.basedir, 'test_files', 'shopify_example.csv'))
        review_row_1 = reviews[0]
        user = self.shopify_importer.create_or_match_user_from_shopify_data(author=review_row_1["author"],
                                                                            email=review_row_1["email"])
        self.assertTrue(isinstance(user, User))
        self.assertEqual(user.email, "john.appleseed@example.com")
        self.assertEqual(user.name, "John Appleseed")
        self.assertEqual(len(User.query.filter_by(email="john.appleseed@example.com").all()), 1)


