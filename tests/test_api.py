import json
import os
import datetime
import base64
import hmac
import hashlib
from flask import url_for
from freezegun import freeze_time
from unittest import TestCase
from webapp import create_app, db, common
from webapp.models import User, Role, Shop, Review, Product, Order
from tests import testing_constants
from config import Constants, basedir
import sensitive
from repopulate import import_tables
from config import Config

class TestFlaskApplication(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app('testing')
        cls.master_client = cls.app.test_client()

        cls.desktop_client = cls.app.test_client()
        cls.mobile_client = cls.app.test_client()

        def override_method(method, ua):
            def om_wrapper(*args, **kwargs):
                kwargs = common.inject_ua(ua, kwargs)
                return getattr(cls.master_client, method)(*args, **kwargs)
            return om_wrapper

        cls.desktop_client.get = override_method('get', Constants.DESKTOP_USER_AGENT)
        cls.desktop_client.post = override_method('post', Constants.DESKTOP_USER_AGENT)
        cls.desktop_client.put = override_method('put', Constants.DESKTOP_USER_AGENT)
        cls.desktop_client.patch = override_method('patch', Constants.DESKTOP_USER_AGENT)
        cls.desktop_client.delete = override_method('delete', Constants.DESKTOP_USER_AGENT)

        cls.mobile_client.get = override_method('get', Constants.MOBILE_USER_AGENT)
        cls.mobile_client.post = override_method('post', Constants.MOBILE_USER_AGENT)
        cls.mobile_client.put = override_method('put', Constants.MOBILE_USER_AGENT)
        cls.mobile_client.patch = override_method('patch', Constants.MOBILE_USER_AGENT)
        cls.mobile_client.delete = override_method('delete', Constants.MOBILE_USER_AGENT)

        cls.app.app_context().push()
        db.session.remove()
        db.drop_all()
        db.create_all()

        db_dir = os.path.join(basedir, 'install', 'db', cls.app.config.get('MODE'))
        import_tables(db, db_dir)

        admin_role = Role.query.filter_by(name=Constants.ADMIN_ROLE).first()
        cls.admin_user = User.query.filter_by(id=1).first()
        assert admin_role in cls.admin_user.roles
        cls.admin_password = sensitive.ADMIN_PASSWORD

        reviewer_role = Role.query.filter_by(name=Constants.REVIEWER_ROLE).first()
        cls.reviewer_user = User.query.filter_by(id=2).first()
        assert cls.reviewer_user.has_role(reviewer_role)
        cls.reviewer_password = sensitive.TEST_REVIEWER_PASSWORD

        shop_owner_role = Role.query.filter_by(name=Constants.SHOP_OWNER_ROLE).first()
        cls.shop_onwer_user = User.query.filter_by(id=3).first()
        assert cls.shop_onwer_user.has_role(shop_owner_role)
        cls.shop_owner_password = sensitive.TEST_SHOP_OWNER_PASSWORD

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()

    def login(self, email, password):
        return self.desktop_client.post('/login', data=dict(
            email=email,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.desktop_client.get('/logout', follow_redirects=True)


class TestAPI(TestFlaskApplication):

    def test_generate_csrf_token_reviewer(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.desktop_client.get("/api/v1/token")
        self.assertEquals(response_actual.status_code, 200)
        jsonified_response = json.loads(response_actual.data)
        self.assertTrue(type(jsonified_response["token"]) is unicode and len(jsonified_response["token"]) > 0)
        self.logout()

    def test_generate_csrf_token_admin(self):
        self.login(self.admin_user.email, self.admin_password)
        response_actual = self.desktop_client.get("/api/v1/token")
        self.assertEquals(response_actual.status_code, 200)
        jsonified_response = json.loads(response_actual.data)
        self.assertTrue(type(jsonified_response["token"]) is unicode and len(jsonified_response["token"]) > 0)
        self.logout()

    def test_generate_csrf_token_shop_owner(self):
        self.login(self.shop_onwer_user.email, self.shop_owner_password)
        response_actual = self.desktop_client.get("/api/v1/token")
        self.assertEquals(response_actual.status_code, 200)
        jsonified_response = json.loads(response_actual.data)
        self.assertTrue(type(jsonified_response["token"]) is unicode and len(jsonified_response["token"]) > 0)
        self.logout()

    def test_authenticate_admin(self):
        payload = json.dumps({"email": self.admin_user.email, "password": self.admin_password})
        response_actual = self.desktop_client.post("/api/v1/auth",
                                           headers={'content-type': 'application/json'},
                                           data=payload)
        self.assertEquals(response_actual.status_code, 200)
        self.assertEquals(response_actual.data, "{}")
        self.logout()

    def test_authenticate_reviewer(self):
        payload = json.dumps({"email": self.reviewer_user.email, "password": self.reviewer_password})
        response_actual = self.desktop_client.post("/api/v1/auth",
                                           headers={'content-type': 'application/json'},
                                           data=payload)
        self.assertEquals(response_actual.status_code, 200)
        self.assertEquals(response_actual.data, "{}")
        self.logout()

    def test_authenticate_shop_owner(self):
        payload = json.dumps({"email": self.shop_onwer_user.email, "password": self.shop_owner_password})
        response_actual = self.desktop_client.post("/api/v1/auth",
                                           headers={'content-type': 'application/json'},
                                           data=payload)
        self.assertEquals(response_actual.status_code, 200)
        self.assertEquals(response_actual.data, "{}")
        self.logout()


    @freeze_time(testing_constants.NEW_REVIEW_CREATED_TS)
    def test_api_post_review_full_pipeline(self):
        split_frozen_time = testing_constants.NEW_REVIEW_CREATED_TS.split('-')
        frozen_time = datetime.datetime(int(split_frozen_time[0]), int(split_frozen_time[1]), int(split_frozen_time[2]))
        # Login as a reviewer
        self.login(self.reviewer_user.email, self.reviewer_password)
        payload = json.dumps({"product_id": testing_constants.NEW_REVIEW_PRODUCT_ID,
                              "body": testing_constants.NEW_REVIEW_BODY,
                              "star_rating": testing_constants.NEW_REVIEW_STARS,
                              "image_url": testing_constants.NEW_REVIEW_IMAGE_URL})
        response_actual = self.desktop_client.post("/api/v1/review",
                                           headers={'content-type': 'application/json'},
                                           data=payload)

        # First, check if API response is good...
        self.assertEquals(response_actual.status_code, 201)
        jsonified_response = json.loads(response_actual.data)
        self.assertTrue('body' in jsonified_response and
                        unicode(testing_constants.NEW_REVIEW_BODY) == jsonified_response['body'])
        self.assertTrue('star_rating' in jsonified_response and
                        testing_constants.NEW_REVIEW_STARS == jsonified_response['star_rating'])
        self.assertTrue('image_url' in jsonified_response and
                        testing_constants.NEW_REVIEW_IMAGE_URL == jsonified_response['image_url'])
        self.assertTrue('product_id' in jsonified_response and
                        testing_constants.NEW_REVIEW_PRODUCT_ID == jsonified_response['product_id'])
        self.assertTrue('password' not in jsonified_response['user'])

        # Check if db records are fine and dandy...
        review_id = jsonified_response['id']
        review = Review.query.filter_by(id=review_id).first()
        self.assertEquals(testing_constants.NEW_REVIEW_BODY, review.body)
        self.assertEquals(testing_constants.NEW_REVIEW_STARS, review.star_rating)
        self.assertEquals(testing_constants.NEW_REVIEW_IMAGE_URL, review.image_url)
        self.assertFalse(review.approval_pending)
        self.assertFalse(review.by_shop_owner)
        self.assertFalse(review.verified_review)
        self.assertEquals(frozen_time, review.created_ts)
        self.assertTrue(review.approved_by_shop)

        # Finally, check that what needs to be rendered, is rendered..
        response_actual = self.desktop_client.get(url_for('client.get_product', product_id=1))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue(testing_constants.NEW_REVIEW_BODY in response_actual.data)
        self.assertTrue(testing_constants.NEW_REVIEW_IMAGE_URL in response_actual.data)
        self.assertTrue(testing_constants.RENDERED_STARS in response_actual.data)
        self.logout()

    def helper_api_post_review_youtube_link(self, body_string):
        self.login(self.reviewer_user.email, self.reviewer_password)
        payload = json.dumps({"product_id": testing_constants.NEW_REVIEW_PRODUCT_ID,
                              "body": body_string})
        response_actual = self.desktop_client.post("/api/v1/review",
                                           headers={'content-type': 'application/json'},
                                           data=payload)

        # First, check if API response is good...
        self.assertEquals(response_actual.status_code, 201)
        jsonified_response = json.loads(response_actual.data)
        self.assertTrue('body' in jsonified_response and
                        unicode(testing_constants.NEW_REVIEW_BODY) == jsonified_response['body'])

        # Check if db records are fine and dandy...
        review_id = jsonified_response['id']
        review = Review.query.filter_by(id=review_id).first()
        self.assertEquals(testing_constants.NEW_REVIEW_BODY, review.body)
        self.assertEquals(
            Constants.YOUTUBE_EMBED_URL.format(youtube_video_id=testing_constants.NEW_REVIEW_YOUTUBE_VIDEO_ID),
            review.youtube_video)

        # Finally, check that what needs to be rendered, is rendered..
        response_actual = self.desktop_client.get(url_for('client.get_product', product_id=1))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue(testing_constants.NEW_REVIEW_BODY in response_actual.data)
        self.assertTrue(testing_constants.RENDERED_YOUTUBE in response_actual.data)
        self.logout()

    def test_api_post_review_youtube_link_at_end_of_body(self):
        self.helper_api_post_review_youtube_link(
            testing_constants.NEW_REVIEW_BODY + ' ' + testing_constants.NEW_REVIEW_YOUTUBE_LINK)

    def test_api_post_review_youtube_link_at_beginning_of_body(self):
        self.helper_api_post_review_youtube_link(
            testing_constants.NEW_REVIEW_YOUTUBE_LINK + ' ' + testing_constants.NEW_REVIEW_BODY)

    def test_api_post_review_youtube_link_middle_of_body(self):
        self.helper_api_post_review_youtube_link(
            ' ' + testing_constants.NEW_REVIEW_YOUTUBE_LINK + ' ' + testing_constants.NEW_REVIEW_BODY)

    def test_api_post_review_shop_owner(self):
        split_frozen_time = testing_constants.NEW_REVIEW_CREATED_TS.split('-')
        frozen_time = datetime.datetime(int(split_frozen_time[0]), int(split_frozen_time[1]), int(split_frozen_time[2]))
        self.login(self.shop_onwer_user.email, self.shop_owner_password)
        payload = json.dumps({"product_id": testing_constants.NEW_REVIEW_PRODUCT_ID})
        response_actual = self.desktop_client.post("/api/v1/review",
                                           headers={'content-type': 'application/json'},
                                           data=payload)

        # First, check if API response is good...
        self.assertEquals(response_actual.status_code, 201)
        jsonified_response = json.loads(response_actual.data)
        self.assertTrue('product_id' in jsonified_response and
                        testing_constants.NEW_REVIEW_PRODUCT_ID == jsonified_response['product_id'])
        self.assertTrue('by_shop_owner' in jsonified_response and jsonified_response['by_shop_owner'])

        # Check if db records are fine and dandy...
        review_id = jsonified_response['id']
        review = Review.query.filter_by(id=review_id).first()
        self.assertTrue(review.by_shop_owner)

        # Finally, check that what needs to be rendered, is rendered..
        response_actual = self.desktop_client.get(url_for('client.get_product', product_id=1))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue(testing_constants.RENDERED_BY_SHOP_OWNER in response_actual.data)
        self.logout()