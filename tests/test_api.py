import json
import datetime
from flask import url_for
from freezegun import freeze_time
from webapp.models import Review
from tests import testing_constants
from config import Constants
from tests.framework import TestFlaskApplication


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
        self.login(self.shop_owner_user.email, self.shop_owner_password)
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
        payload = json.dumps({"email": self.shop_owner_user.email, "password": self.shop_owner_password})
        response_actual = self.desktop_client.post("/api/v1/auth",
                                           headers={'content-type': 'application/json'},
                                           data=payload)
        self.assertEquals(response_actual.status_code, 200)
        self.assertEquals(response_actual.data, "{}")
        self.logout()

    def test_get_reviews_status_code(self):
        response_actual = self.desktop_client.get("/api/v1/review")
        self.assertEquals(response_actual.status_code, 200)

    def test_get_reviews_not_empty(self):
        response_actual = self.desktop_client.get("/api/v1/review")
        self.assertEquals(response_actual.status_code, 200)
        response_json_dict = json.loads(response_actual.data)
        self.assertTrue(len(response_json_dict["objects"]) > 0)

    def test_get_reviews_has_review_id1(self):
        response_actual = self.desktop_client.get("/api/v1/review")
        response_json_dict = json.loads(response_actual.data)
        review_dict = {"id":None}
        for review in response_json_dict["objects"]:
            if review["id"] == 1:
                review_dict = review
        self.assertEquals(review_dict["id"], 1)

    def test_get_reviews_review_id1_body(self):
        response_actual = self.desktop_client.get("/api/v1/review")
        response_json_dict = json.loads(response_actual.data)
        review_dict = {"id":None,"body":None}
        for review in response_json_dict["objects"]:
            if review["id"] == 1:
                review_dict = review
        self.assertEquals(review_dict["body"], "Perfect unusual accessory for a normal day.")

    def test_get_reviews_review_id1_user(self):
        response_actual = self.desktop_client.get("/api/v1/review")
        response_json_dict = json.loads(response_actual.data)
        review_dict = {"id":None, "user":None}
        for review in response_json_dict["objects"]:
            if review["id"] == 1:
                review_dict = review
        self.assertEquals(review_dict["user"], {'is_shop_owner': False, 'image_url': 'https://opinew.com/media/user/3_rose_castro.jpg', 'email': 'rose.castro@example.com', 'name': 'Rose Castro', 'id': 2})

    def test_get_reviews_review_id1_image_url(self):
        response_actual = self.desktop_client.get("/api/v1/review")
        response_json_dict = json.loads(response_actual.data)
        review_dict = {"id":None, "image_url":None}
        for review in response_json_dict["objects"]:
            if review["id"] == 1:
                review_dict = review
        self.assertEquals(review_dict["image_url"], "barbara_earrings.jpg")

    def test_get_reviews_review_id1_star_rating(self):
        response_actual = self.desktop_client.get("/api/v1/review")
        response_json_dict = json.loads(response_actual.data)
        review_dict = {"id":None, "star_rating":None}
        for review in response_json_dict["objects"]:
            if review["id"] == 1:
                review_dict = review
        self.assertEquals(review_dict["star_rating"], 1)

    def test_get_reviews_review_id1_is_verified(self):
        response_actual = self.desktop_client.get("/api/v1/review")
        response_json_dict = json.loads(response_actual.data)
        review_dict = {"id":None, "verified_review":None}
        for review in response_json_dict["objects"]:
            if review["id"] == 1:
                review_dict = review
        self.assertEquals(review_dict["verified_review"], True)

    def test_get_reviews_review_id1_product_id(self):
        response_actual = self.desktop_client.get("/api/v1/review")
        response_json_dict = json.loads(response_actual.data)
        review_dict = {"id":None,"product_id":None}
        for review in response_json_dict["objects"]:
            if review["id"] == 1:
                review_dict = review
        self.assertEquals(review_dict["product_id"], 1)

    def test_get_reviews_review_id1_product(self):
        response_actual = self.desktop_client.get("/api/v1/review")
        response_json_dict = json.loads(response_actual.data)
        review_dict = {"id":None,"product":None}
        for review in response_json_dict["objects"]:
            if review["id"] == 1:
                review_dict = review
        self.assertEquals(review_dict["product"], {'category': None, 'product_type': None, 'name': 'Ear rings', 'review_help': None, 'platform_product_id': '1', 'short_description': None, 'plugin_views': 0, 'shop_id': 2, 'image_url': 'https://opinew.com/media/review/earrings.jpg', 'active': True, 'id': 1})

    def test_get_reviews_accept_query_params(self):
        response_actual = self.desktop_client.get("/api/v1/review?q={\"order_by\": [{\"field\": \"created_ts\", \"direction\":\"desc\"}], \"offset\":10}")
        self.assertEquals(response_actual.status_code, 200)

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
        self.login(self.shop_owner_user.email, self.shop_owner_password)
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