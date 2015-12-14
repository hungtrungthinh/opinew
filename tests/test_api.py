import json
import datetime
from flask import url_for
from freezegun import freeze_time
from webapp.models import Review, Notification, User, Order,\
    Customer, Product, Shop, ReviewRequest, UserLegacy
from tests import testing_constants
from config import Constants
from tests.framework import TestFlaskApplication, expect_mail
from flask.ext.restless import ProcessingException
from webapp import db, mail
from webapp.exceptions import ExceptionMessages


class TestAPI(TestFlaskApplication):
    ################CSRF TOKEN##################

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

    ###########AUTHENTICATE#############

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

    ###########REVIEWS###############

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
        review_dict = {"id": None}
        for review in response_json_dict["objects"]:
            if review["id"] == 1:
                review_dict = review
        self.assertEquals(review_dict["id"], 1)

    def test_get_reviews_review_id1_body(self):
        response_actual = self.desktop_client.get("/api/v1/review")
        response_json_dict = json.loads(response_actual.data)
        review_dict = {"id": None, "body": None}
        for review in response_json_dict["objects"]:
            if review["id"] == 1:
                review_dict = review
        self.assertEquals(review_dict["body"], "Perfect unusual accessory for a normal day.")

    def test_get_reviews_review_id1_user(self):
        response_actual = self.desktop_client.get("/api/v1/review")
        response_json_dict = json.loads(response_actual.data)
        review_dict = {"id": None, "user": None}
        for review in response_json_dict["objects"]:
            if review["id"] == 1:
                review_dict = review
        self.assertEquals(review_dict["user"],
                          {'is_shop_owner': False, 'image_url': 'https://opinew.com/media/user/3_rose_castro.jpg',
                           'email': 'rose.castro@example.com', 'name': 'Rose Castro', 'id': 2})

    def test_get_reviews_review_id1_image_url(self):
        response_actual = self.desktop_client.get("/api/v1/review")
        response_json_dict = json.loads(response_actual.data)
        review_dict = {"id": None, "image_url": None}
        for review in response_json_dict["objects"]:
            if review["id"] == 1:
                review_dict = review
        self.assertEquals(review_dict["image_url"], "barbara_earrings.jpg")

    def test_get_reviews_review_id1_star_rating(self):
        response_actual = self.desktop_client.get("/api/v1/review")
        response_json_dict = json.loads(response_actual.data)
        review_dict = {"id": None, "star_rating": None}
        for review in response_json_dict["objects"]:
            if review["id"] == 1:
                review_dict = review
        self.assertEquals(review_dict["star_rating"], 1)

    def test_get_reviews_review_id1_is_verified(self):
        response_actual = self.desktop_client.get("/api/v1/review")
        response_json_dict = json.loads(response_actual.data)
        review_dict = {"id": None, "verified_review": None}
        for review in response_json_dict["objects"]:
            if review["id"] == 1:
                review_dict = review
        self.assertEquals(review_dict["verified_review"], True)

    def test_get_reviews_review_id1_product_id(self):
        response_actual = self.desktop_client.get("/api/v1/review")
        response_json_dict = json.loads(response_actual.data)
        review_dict = {"id": None, "product_id": None}
        for review in response_json_dict["objects"]:
            if review["id"] == 1:
                review_dict = review
        self.assertEquals(review_dict["product_id"], 1)

    def test_get_reviews_review_id1_product(self):
        response_actual = self.desktop_client.get("/api/v1/review")
        response_json_dict = json.loads(response_actual.data)
        review_dict = {"id": None, "product": None}
        for review in response_json_dict["objects"]:
            if review["id"] == 1:
                review_dict = review
        self.assertEquals(review_dict["product"],
                          {'category': None, 'product_type': None, 'name': 'Ear rings', 'review_help': None,
                           'platform_product_id': '1', 'short_description': None, 'plugin_views': 0, 'shop_id': 2,
                           'image_url': 'https://opinew.com/media/review/earrings.jpg', 'active': True, 'id': 1})

    def test_get_reviews_accept_query_params(self):
        response_actual = self.desktop_client.get(
            "/api/v1/review?q={\"order_by\": [{\"field\": \"created_ts\", \"direction\":\"desc\"}], \"offset\":10}")
        self.assertEquals(response_actual.status_code, 200)

    ##########TEST SINGLE REVIEW GET##############
    def test_get_review_id1(self):
        response_actual = self.desktop_client.get("/api/v1/review/1")
        response_json_dict = json.loads(response_actual.data)
        self.assertTrue(response_json_dict is not None)
        self.assertTrue(response_json_dict != {})

    def test_get_review_id1_product(self):
        response_actual = self.desktop_client.get("/api/v1/review/1")
        response_json_dict = json.loads(response_actual.data)
        self.assertEquals(response_json_dict["product"],
                          {'category': None, 'product_type': None, 'name': 'Ear rings', 'review_help': None,
                           'platform_product_id': '1', 'short_description': None, 'plugin_views': 0, 'shop_id': 2,
                           'image_url': 'https://opinew.com/media/review/earrings.jpg', 'active': True, 'id': 1})

    ########Review POST#########
    def helper_check_review(self, response_actual):
        split_frozen_time = testing_constants.NEW_REVIEW_CREATED_TS.split('-')
        frozen_time = datetime.datetime(int(split_frozen_time[0]), int(split_frozen_time[1]), int(split_frozen_time[2]))
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
        self.assertTrue(jsonified_response['user'] is not None and 'password' not in jsonified_response['user'])

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

    def helper_check_verified_review(self, response_actual):
        split_frozen_time = testing_constants.NEW_REVIEW_CREATED_TS.split('-')
        frozen_time = datetime.datetime(int(split_frozen_time[0]), int(split_frozen_time[1]), int(split_frozen_time[2]))
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
        self.assertTrue(jsonified_response['user'] is not None and 'password' not in jsonified_response['user'])

        # Check if db records are fine and dandy...
        review_id = jsonified_response['id']
        review = Review.query.filter_by(id=review_id).first()
        self.assertEquals(testing_constants.NEW_REVIEW_BODY, review.body)
        self.assertEquals(testing_constants.NEW_REVIEW_STARS, review.star_rating)
        self.assertEquals(testing_constants.NEW_REVIEW_IMAGE_URL, review.image_url)
        self.assertFalse(review.approval_pending)
        self.assertFalse(review.by_shop_owner)
        self.assertTrue(review.verified_review)
        self.assertEquals(frozen_time, review.created_ts)
        self.assertTrue(review.approved_by_shop)

        # Finally, check that what needs to be rendered, is rendered..
        response_actual = self.desktop_client.get(url_for('client.get_product', product_id=1))
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue(testing_constants.NEW_REVIEW_BODY in response_actual.data)
        self.assertTrue(testing_constants.NEW_REVIEW_IMAGE_URL in response_actual.data)
        self.assertTrue(testing_constants.RENDERED_STARS in response_actual.data)

    @freeze_time(testing_constants.NEW_REVIEW_CREATED_TS)
    def test_api_post_review_full_pipeline_EXISTING_USER_logged_in(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        params = {"product_id": testing_constants.NEW_REVIEW_PRODUCT_ID,
                  "body": testing_constants.NEW_REVIEW_BODY,
                  "star_rating": testing_constants.NEW_REVIEW_STARS,
                  "image_url": testing_constants.NEW_REVIEW_IMAGE_URL}
        payload = json.dumps(params)
        response_actual = self.desktop_client.post("/api/v1/review",
                                                   headers={'content-type': 'application/json'},
                                                   data=payload)
        self.helper_check_review(response_actual)
        self.logout()

    @expect_mail
    @freeze_time(testing_constants.NEW_REVIEW_CREATED_TS)
    def test_api_post_review_full_pipeline_not_logged_in_NEW_USER(self):
        self.refresh_db()
        params = {"product_id": testing_constants.NEW_REVIEW_PRODUCT_ID,
                  "body": testing_constants.NEW_REVIEW_BODY,
                  "star_rating": testing_constants.NEW_REVIEW_STARS,
                  "image_url": testing_constants.NEW_REVIEW_IMAGE_URL,
                  "g-recaptcha-response": testing_constants.RECAPTCHA_FAKE_PASS,
                  "user_name": testing_constants.NEW_USER_NAME,
                  "user_email": testing_constants.NEW_USER_EMAIL}
        payload = json.dumps(params)
        response_actual = self.desktop_client.post("/api/v1/review",
                                           headers={'content-type': 'application/json'},
                                           data=payload)

        self.assertEquals(len(self.outbox), 1)
        # TODO
        # self.assertEquals(len(outbox[0].send_to), 1)
        # self.assertEquals(outbox[0].send_to.pop(), testing_constants.NEW_USER_EMAIL)
        # self.assertEquals(outbox[0].subject, Constants.DEFAULT_NEW_REVIEWER_SUBJECT)
        # self.assertTrue(testing_constants.NEW_USER_NAME in outbox[0].body)
        # self.assertTrue(testing_constants.NEW_PRODUCT_NAME in outbox[0].body)
        # self.assertTrue(testing_constants.NEW_SHOP_NAME in outbox[0].body)
        self.helper_check_review(response_actual)

    @freeze_time(testing_constants.NEW_REVIEW_CREATED_TS)
    def test_api_post_review_full_pipeline_EXISTING_USER_not_logged_in(self):
        self.refresh_db()
        params = {"product_id": testing_constants.NEW_REVIEW_PRODUCT_ID,
                  "body": testing_constants.NEW_REVIEW_BODY,
                  "star_rating": testing_constants.NEW_REVIEW_STARS,
                  "image_url": testing_constants.NEW_REVIEW_IMAGE_URL,
                  "g-recaptcha-response": testing_constants.RECAPTCHA_FAKE_PASS,
                  "user_name": self.reviewer_user.name,
                  "user_email": self.reviewer_user.email,
                  "user_password": self.reviewer_password}
        payload = json.dumps(params)
        response_actual = self.desktop_client.post("/api/v1/review",
                                           headers={'content-type': 'application/json'},
                                           data=payload)

        #self.assertEquals(len(self.outbox), 0)
        # TODO
        # self.assertEquals(len(outbox[0].send_to), 1)
        # self.assertEquals(outbox[0].send_to.pop(), testing_constants.NEW_USER_EMAIL)
        # self.assertEquals(outbox[0].subject, Constants.DEFAULT_NEW_REVIEWER_SUBJECT)
        # self.assertTrue(testing_constants.NEW_USER_NAME in outbox[0].body)
        # self.assertTrue(testing_constants.NEW_PRODUCT_NAME in outbox[0].body)
        # self.assertTrue(testing_constants.NEW_SHOP_NAME in outbox[0].body)
        self.helper_check_review(response_actual)

    @freeze_time(testing_constants.NEW_REVIEW_CREATED_TS)
    def test_api_post_review_full_pipeline_EXISTING_USER_not_logged_in_bad_passwd(self):
        self.refresh_db()
        params = {"product_id": testing_constants.NEW_REVIEW_PRODUCT_ID,
                  "body": testing_constants.NEW_REVIEW_BODY,
                  "star_rating": testing_constants.NEW_REVIEW_STARS,
                  "image_url": testing_constants.NEW_REVIEW_IMAGE_URL,
                  "g-recaptcha-response": testing_constants.RECAPTCHA_FAKE_PASS,
                  "user_name": self.reviewer_user.name,
                  "user_email": self.reviewer_user.email,
                  "user_password": testing_constants.USER_BOGUS_PWD}
        payload = json.dumps(params)
        response_actual = self.desktop_client.post("/api/v1/review",
                                           headers={'content-type': 'application/json'},
                                           data=payload)

        self.assertEqual(response_actual.status_code, 401)
        jsonified_response = json.loads(response_actual.data)
        expected_response = {'message': 'unauthorized'}
        self.assertEquals(jsonified_response, expected_response)

    @freeze_time(testing_constants.NEW_REVIEW_CREATED_TS)
    def test_api_post_review_full_pipeline_EXISTING_USER_not_logged_in_bad_username(self):
        self.refresh_db()
        params = {"product_id": testing_constants.NEW_REVIEW_PRODUCT_ID,
                  "body": testing_constants.NEW_REVIEW_BODY,
                  "star_rating": testing_constants.NEW_REVIEW_STARS,
                  "image_url": testing_constants.NEW_REVIEW_IMAGE_URL,
                  "g-recaptcha-response": testing_constants.RECAPTCHA_FAKE_PASS,
                  "user_name": self.reviewer_user.name,
                  "user_email": testing_constants.USER_BOGUS_EMAIL,
                  "user_password": self.reviewer_password}
        payload = json.dumps(params)
        response_actual = self.desktop_client.post("/api/v1/review",
                                           headers={'content-type': 'application/json'},
                                           data=payload)

        self.assertEqual(response_actual.status_code, 401)
        jsonified_response = json.loads(response_actual.data)
        expected_response = {'message': 'unauthorized'}
        self.assertEquals(jsonified_response, expected_response)

    def test_api_post_review_not_logged_in_no_recaptcha(self):
        params = {"product_id": testing_constants.NEW_REVIEW_PRODUCT_ID,
                  "body": testing_constants.NEW_REVIEW_BODY,
                  "star_rating": testing_constants.NEW_REVIEW_STARS,
                  "image_url": testing_constants.NEW_REVIEW_IMAGE_URL,
                  "user_name": testing_constants.NEW_USER_NAME,
                  "user_email": testing_constants.NEW_USER_EMAIL}
        payload = json.dumps(params)
        response_actual = self.desktop_client.post("/api/v1/review",
                                                   headers={'content-type': 'application/json'},
                                                   data=payload)
        self.assertEquals(response_actual.status_code, 401)
        jsonified_response = json.loads(response_actual.data)
        expected_response = {'message': ExceptionMessages.MISSING_PARAM % 'g-recaptcha-response'}
        self.assertEquals(jsonified_response, expected_response)

    def test_api_post_review_not_logged_failing_recaptcha(self):
        params = {"product_id": testing_constants.NEW_REVIEW_PRODUCT_ID,
                  "body": testing_constants.NEW_REVIEW_BODY,
                  "star_rating": testing_constants.NEW_REVIEW_STARS,
                  "image_url": testing_constants.NEW_REVIEW_IMAGE_URL,
                  "g-recaptcha-response": testing_constants.RECAPTCHA_FAKE_FAIL,
                  "user_name": testing_constants.NEW_USER_NAME,
                  "user_email": testing_constants.NEW_USER_EMAIL}
        payload = json.dumps(params)
        response_actual = self.desktop_client.post("/api/v1/review",
                                                   headers={'content-type': 'application/json'},
                                                   data=payload)
        self.assertEquals(response_actual.status_code, 401)
        jsonified_response = json.loads(response_actual.data)
        expected_response = {'message': ExceptionMessages.CAPTCHA_FAIL}
        self.assertEquals(jsonified_response, expected_response)

    @freeze_time(testing_constants.NEW_REVIEW_CREATED_TS)
    def test_api_post_review_full_pipeline_EXISTING_USER_not_logged_in_POST_EMAIL(self):
        """
        Use case when we post the review after clicking thorough from the email
        review request. We have additional review_request_id and review_request_token
        parameters
        """
        self.refresh_db()
        order = Order()
        product = Product.get_by_id(1)
        order.user = self.reviewer_user
        customer = Customer(user=self.shop_owner_user)
        shop = Shop(name=testing_constants.NEW_SHOP_NAME)
        shop.owner = self.shop_owner_user
        product.shop = shop
        order.shop = shop
        order.products.append(product)

        #creates a review request and returns a token associated with it
        review_request_token = ReviewRequest.create(to_user=self.reviewer_user, from_customer=customer,
                                                           for_product=product, for_shop=shop, for_order=order)
        review_request = ReviewRequest.query.filter_by(token=review_request_token).first()

        params = {"product_id": testing_constants.NEW_REVIEW_PRODUCT_ID,
                  "body": testing_constants.NEW_REVIEW_BODY,
                  "star_rating": testing_constants.NEW_REVIEW_STARS,
                  "image_url": testing_constants.NEW_REVIEW_IMAGE_URL,
                  "g-recaptcha-response": testing_constants.RECAPTCHA_FAKE_PASS,
                  "user_name": self.reviewer_user.name,
                  "user_email": self.reviewer_user.email,
                  "user_password": self.reviewer_password,
                  "review_request_token": review_request_token,
                  "review_request_id": review_request.id}
        payload = json.dumps(params)
        response_actual = self.desktop_client.post("/api/v1/review",
                                           headers={'content-type': 'application/json'},
                                           data=payload)

        self.assertEqual(response_actual.status_code, 201)
        self.helper_check_verified_review(response_actual)
        self.logout()

    @expect_mail
    @freeze_time(testing_constants.NEW_REVIEW_CREATED_TS)
    def test_api_post_review_full_pipeline_Legacy_User_POST_EMAIL(self):
        """
        Use case when:
        We haven't posted a review before and this is the first time we receive the review request.
        There is temporary LegacyUser in the db.
        On posting of the review Opinew
        1.deletes the LegacyUser,
        2.creates a normal user and transfers the data(orders and review requests) from legacy user,
        3. sends post-registration email,
        4.logs user in
        We have additional review_request_id and review_request_token parameters because of posting
        from inside the email review request link with a token.
        """
        self.refresh_db()
        legacy_user = UserLegacy(email=testing_constants.NEW_USER_EMAIL, name=testing_constants.NEW_USER_NAME)
        order = Order()
        product = Product.get_by_id(1)
        order.user_legacy = legacy_user
        customer = Customer(user=self.shop_owner_user)
        shop = Shop(name=testing_constants.NEW_SHOP_NAME)
        shop.owner = self.shop_owner_user
        product.shop = shop
        order.shop = shop
        order.products.append(product)

        #creates a review request and returns a token associated with it
        review_request_token = ReviewRequest.create(to_user=legacy_user, from_customer=customer,
                                                    for_product=product, for_shop=shop, for_order=order)
        review_request = ReviewRequest.query.filter_by(token=review_request_token).first()

        params = {"product_id": testing_constants.NEW_REVIEW_PRODUCT_ID,
                  "body": testing_constants.NEW_REVIEW_BODY,
                  "star_rating": testing_constants.NEW_REVIEW_STARS,
                  "image_url": testing_constants.NEW_REVIEW_IMAGE_URL,
                  "g-recaptcha-response": testing_constants.RECAPTCHA_FAKE_PASS,
                  "user_name": legacy_user.name,
                  "user_email": legacy_user.email,
                  "review_request_token": review_request_token,
                  "review_request_id": review_request.id}
        payload = json.dumps(params)
        response_actual = self.desktop_client.post("/api/v1/review",
                                           headers={'content-type': 'application/json'},
                                           data=payload)

        self.assertEqual(response_actual.status_code, 201)
        self.helper_check_verified_review(response_actual)
        self.logout()


    @expect_mail
    @freeze_time(testing_constants.NEW_REVIEW_CREATED_TS)
    def test_api_post_review_full_pipeline_Legacy_User_POST_EMAIL_multiple_rev_requests_logged_in_after_1st_review(self):
        """
        Use case when:
        We haven't posted a review before and this is the first time we receive the review request.
        There is temporary LegacyUser in the db.
        On posting of the review Opinew
        1.deletes the LegacyUser,
        2.creates a normal user and transfers the data(orders and review requests) from legacy user,
        3. sends post-registration email,
        4.logs user in
        We have additional review_request_id and review_request_token parameters because of posting
        from inside the email review request link with a token.
        """
        self.refresh_db()
        legacy_user = UserLegacy(email=testing_constants.NEW_USER_EMAIL, name=testing_constants.NEW_USER_NAME)
        order = Order()
        product1 = Product.get_by_id(1)
        product2 = Product.get_by_id(2)
        product1_id = product1.id
        product2_id = product2.id
        order.user_legacy = legacy_user
        customer = Customer(user=self.shop_owner_user)
        shop = Shop(name=testing_constants.NEW_SHOP_NAME)
        shop.owner = self.shop_owner_user
        product1.shop = shop
        product2.shop = shop
        order.shop = shop
        order.products.append(product1)
        order.products.append(product2)

        #creates a review request and returns a token associated with it
        review_request_token1 = ReviewRequest.create(to_user=legacy_user, from_customer=customer,
                                                    for_product=product1, for_shop=shop, for_order=order)
        review_request_token2 = ReviewRequest.create(to_user=legacy_user, from_customer=customer,
                                                    for_product=product2, for_shop=shop, for_order=order)
        review_request1 = ReviewRequest.query.filter_by(token=review_request_token1).first()

        params1 = {"product_id": product1_id,
                  "body": testing_constants.NEW_REVIEW_BODY,
                  "star_rating": testing_constants.NEW_REVIEW_STARS,
                  "image_url": testing_constants.NEW_REVIEW_IMAGE_URL,
                  "g-recaptcha-response": testing_constants.RECAPTCHA_FAKE_PASS,
                  "user_name": testing_constants.NEW_USER_NAME,
                  "user_email": testing_constants.NEW_USER_EMAIL,
                  "review_request_token": review_request_token1,
                  "review_request_id": review_request1.id}
        payload1 = json.dumps(params1)
        response_actual = self.desktop_client.post("/api/v1/review",
                                           headers={'content-type': 'application/json'},
                                           data=payload1)
        self.assertEqual(response_actual.status_code, 201)
        self.helper_check_verified_review(response_actual)

        review_request2 = ReviewRequest.query.filter_by(token=review_request_token2).first()
        created_normal_user = User.get_by_email(testing_constants.NEW_USER_EMAIL)
        ###SECOND review request link from the email
        params2 = {"product_id": product2_id,
                  "body": testing_constants.NEW_REVIEW_BODY,
                  "star_rating": testing_constants.NEW_REVIEW_STARS,
                  "image_url": testing_constants.NEW_REVIEW_IMAGE_URL,
                  "review_request_token": review_request_token2,
                  "review_request_id": review_request2.id}
        payload2 = json.dumps(params2)
        response_actual2 = self.desktop_client.post("/api/v1/review",
                                           headers={'content-type': 'application/json'},
                                           data=payload2)
        self.assertEqual(response_actual2.status_code, 201)
        self.logout()

    @expect_mail
    @freeze_time(testing_constants.NEW_REVIEW_CREATED_TS)
    def test_api_post_review_full_pipeline_Legacy_User_POST_EMAIL_multiple_rev_requests_logout_after_1st_review(self):
        """
        Use case when:
        We haven't posted a review before and this is the first time we receive the review request.
        There is temporary LegacyUser in the db.
        On posting of the review Opinew
        1.deletes the LegacyUser,
        2.creates a normal user and transfers the data(orders and review requests) from legacy user,
        3. sends post-registration email,
        4.logs user in
        We have additional review_request_id and review_request_token parameters because of posting
        from inside the email review request link with a token.
        """
        self.refresh_db()
        legacy_user = UserLegacy(email=testing_constants.NEW_USER_EMAIL, name=testing_constants.NEW_USER_NAME)
        order = Order()
        product1 = Product.get_by_id(1)
        product2 = Product.get_by_id(2)
        product1_id = product1.id
        product2_id = product2.id
        order.user_legacy = legacy_user
        customer = Customer(user=self.shop_owner_user)
        shop = Shop(name=testing_constants.NEW_SHOP_NAME)
        shop.owner = self.shop_owner_user
        product1.shop = shop
        product2.shop = shop
        order.shop = shop
        order.products.append(product1)
        order.products.append(product2)

        #creates a review request and returns a token associated with it
        review_request_token1 = ReviewRequest.create(to_user=legacy_user, from_customer=customer,
                                                    for_product=product1, for_shop=shop, for_order=order)
        review_request_token2 = ReviewRequest.create(to_user=legacy_user, from_customer=customer,
                                                    for_product=product2, for_shop=shop, for_order=order)
        review_request1 = ReviewRequest.query.filter_by(token=review_request_token1).first()

        params1 = {"product_id": product1_id,
                  "body": testing_constants.NEW_REVIEW_BODY,
                  "star_rating": testing_constants.NEW_REVIEW_STARS,
                  "image_url": testing_constants.NEW_REVIEW_IMAGE_URL,
                  "g-recaptcha-response": testing_constants.RECAPTCHA_FAKE_PASS,
                  "user_name": testing_constants.NEW_USER_NAME,
                  "user_email": testing_constants.NEW_USER_EMAIL,
                  "review_request_token": review_request_token1,
                  "review_request_id": review_request1.id}
        payload1 = json.dumps(params1)
        response_actual = self.desktop_client.post("/api/v1/review",
                                           headers={'content-type': 'application/json'},
                                           data=payload1)
        self.assertEqual(response_actual.status_code, 201)
        self.helper_check_verified_review(response_actual)
        self.logout()

        review_request2 = ReviewRequest.query.filter_by(token=review_request_token2).first()
        created_normal_user = User.get_by_email(testing_constants.NEW_USER_EMAIL)
        ###SECOND review request link from the email
        params2 = {"product_id": product2_id,
                  "body": testing_constants.NEW_REVIEW_BODY,
                  "star_rating": testing_constants.NEW_REVIEW_STARS,
                  "image_url": testing_constants.NEW_REVIEW_IMAGE_URL,
                  "g-recaptcha-response": testing_constants.RECAPTCHA_FAKE_PASS,
                  "user_name": created_normal_user.name,
                  "user_email": created_normal_user.email,
                  "user_password": created_normal_user.temp_password,
                  "review_request_token": review_request_token2,
                  "review_request_id": review_request2.id}
        payload2 = json.dumps(params2)
        response_actual2 = self.desktop_client.post("/api/v1/review",
                                           headers={'content-type': 'application/json'},
                                           data=payload2)
        self.assertEqual(response_actual2.status_code, 201)
        self.logout()





    def test_api_post_review_not_logged_no_name(self):
        params = {"product_id": testing_constants.NEW_REVIEW_PRODUCT_ID,
                  "body": testing_constants.NEW_REVIEW_BODY,
                  "star_rating": testing_constants.NEW_REVIEW_STARS,
                  "image_url": testing_constants.NEW_REVIEW_IMAGE_URL,
                  "g-recaptcha-response": testing_constants.RECAPTCHA_FAKE_PASS,
                  "user_email": testing_constants.NEW_USER_EMAIL}
        payload = json.dumps(params)
        response_actual = self.desktop_client.post("/api/v1/review",
                                                   headers={'content-type': 'application/json'},
                                                   data=payload)
        self.assertEquals(response_actual.status_code, 401)
        jsonified_response = json.loads(response_actual.data)
        expected_response = {'message': ExceptionMessages.MISSING_PARAM % 'user_name'}
        self.assertEquals(jsonified_response, expected_response)

    def test_api_post_review_not_logged_no_email(self):
        params = {"product_id": testing_constants.NEW_REVIEW_PRODUCT_ID,
                  "body": testing_constants.NEW_REVIEW_BODY,
                  "star_rating": testing_constants.NEW_REVIEW_STARS,
                  "image_url": testing_constants.NEW_REVIEW_IMAGE_URL,
                  "g-recaptcha-response": testing_constants.RECAPTCHA_FAKE_PASS,
                  "user_name": testing_constants.NEW_USER_NAME}
        payload = json.dumps(params)
        response_actual = self.desktop_client.post("/api/v1/review",
                                                   headers={'content-type': 'application/json'},
                                                   data=payload)
        self.assertEquals(response_actual.status_code, 401)
        jsonified_response = json.loads(response_actual.data)
        expected_response = {'message': ExceptionMessages.MISSING_PARAM % 'user_email'}
        self.assertEquals(jsonified_response, expected_response)

    def test_api_post_review_not_logged_existing_user(self):
        # add existing user
        existing_user = User(email=testing_constants.NEW_USER_EMAIL)
        db.session.add(existing_user)
        db.session.commit()

        # test
        params = {"product_id": testing_constants.NEW_REVIEW_PRODUCT_ID,
                  "body": testing_constants.NEW_REVIEW_BODY,
                  "star_rating": testing_constants.NEW_REVIEW_STARS,
                  "image_url": testing_constants.NEW_REVIEW_IMAGE_URL,
                  "g-recaptcha-response": testing_constants.RECAPTCHA_FAKE_PASS,
                  "user_name": testing_constants.NEW_USER_NAME,
                  "user_email": testing_constants.NEW_USER_EMAIL}
        payload = json.dumps(params)
        response_actual = self.desktop_client.post("/api/v1/review",
                                                   headers={'content-type': 'application/json'},
                                                   data=payload)
        self.assertEquals(response_actual.status_code, 401)
        jsonified_response = json.loads(response_actual.data)
        expected_response = {'message': ExceptionMessages.USER_EXISTS % testing_constants.NEW_USER_EMAIL}
        self.assertEquals(jsonified_response, expected_response)

        # delete user
        db.session.delete(existing_user)
        db.session.commit()

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

    ###########REVIEW LIKE###############

    def test_review_like_first_time(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        payload = json.dumps({"review_id": 1})
        response_actual = self.desktop_client.post("/api/v1/review_like",
                                                   headers={'content-type': 'application/json'},
                                                   data=payload)
        self.assertEquals(response_actual.status_code, 201)
        self.logout()
        self.refresh_db()

    def test_review_unlike(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        payload1 = json.dumps({"review_id": 1})
        self.desktop_client.post("/api/v1/review_like",
                                 headers={'content-type': 'application/json'},
                                 data=payload1)

        payload2 = json.dumps({"review_id": 1, "action": '0'})
        response_actual = self.desktop_client.patch("/api/v1/review_like/1",
                                                    headers={'content-type': 'application/json'},
                                                    data=payload2)
        response_json_dict = json.loads(response_actual.data)
        self.assertEquals(response_json_dict["action"], 0)
        self.logout()
        self.refresh_db()

    def test_review_like_again(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        payload1 = json.dumps({"review_id": 1})
        self.desktop_client.post("/api/v1/review_like",
                                 headers={'content-type': 'application/json'},
                                 data=payload1)

        payload2 = json.dumps({"review_id": 1, "action": '0'})
        self.desktop_client.patch("/api/v1/review_like/1",
                                  headers={'content-type': 'application/json'},
                                  data=payload2)

        payload3 = json.dumps({"review_id": 1, "action": '1'})
        response_actual = self.desktop_client.patch("/api/v1/review_like/1",
                                                    headers={'content-type': 'application/json'},
                                                    data=payload3)
        response_json_dict = json.loads(response_actual.data)
        self.assertEquals(response_json_dict["action"], 1)
        self.logout()
        self.refresh_db()

    ###########REVIEW REPORT###############

    def test_review_report_first_time(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        payload = json.dumps({"review_id": 1})
        response_actual = self.desktop_client.post("/api/v1/review_report",
                                                   headers={'content-type': 'application/json'},
                                                   data=payload)
        self.assertEquals(response_actual.status_code, 201)
        self.logout()
        self.refresh_db()

    def test_review_unreport(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        payload1 = json.dumps({"review_id": 1})
        self.desktop_client.post("/api/v1/review_report",
                                 headers={'content-type': 'application/json'},
                                 data=payload1)

        payload2 = json.dumps({"review_id": 1, "action": '0'})
        response_actual = self.desktop_client.patch("/api/v1/review_report/1",
                                                    headers={'content-type': 'application/json'},
                                                    data=payload2)
        response_json_dict = json.loads(response_actual.data)
        self.assertEquals(response_json_dict["action"], 0)
        self.logout()
        self.refresh_db()

    def test_review_report_again(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        payload1 = json.dumps({"review_id": 1})
        self.desktop_client.post("/api/v1/review_report",
                                 headers={'content-type': 'application/json'},
                                 data=payload1)

        payload2 = json.dumps({"review_id": 1, "action": '0'})
        self.desktop_client.patch("/api/v1/review_report/1",
                                  headers={'content-type': 'application/json'},
                                  data=payload2)

        payload3 = json.dumps({"review_id": 1, "action": '1'})
        response_actual = self.desktop_client.patch("/api/v1/review_report/1",
                                                    headers={'content-type': 'application/json'},
                                                    data=payload3)
        response_json_dict = json.loads(response_actual.data)
        self.assertEquals(response_json_dict["action"], 1)
        self.logout()
        self.refresh_db()

    ###########REVIEW FEATURE REVIEWER###############

    def test_review_feature_first_time_by_reviewer(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        payload = json.dumps({"review_id": 1})
        self.desktop_client.post("/api/v1/review_feature",
                                 headers={'content-type': 'application/json'},
                                 data=payload)
        self.assertRaises(ProcessingException)
        self.logout()
        self.refresh_db()

    def test_review_unfeature_by_reviewer(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        payload1 = json.dumps({"review_id": 1})
        self.desktop_client.post("/api/v1/review_feature",
                                 headers={'content-type': 'application/json'},
                                 data=payload1)

        payload2 = json.dumps({"review_id": 1, "action": '0'})
        response_actual = self.desktop_client.patch("/api/v1/review_feature/1",
                                                    headers={'content-type': 'application/json'},
                                                    data=payload2)
        self.assertRaises(ProcessingException)
        self.logout()
        self.refresh_db()

    def test_review_feature_again_by_reviewer(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        payload1 = json.dumps({"review_id": 1})
        self.desktop_client.post("/api/v1/review_feature",
                                 headers={'content-type': 'application/json'},
                                 data=payload1)

        payload2 = json.dumps({"review_id": 1, "action": '0'})
        self.desktop_client.patch("/api/v1/review_feature/1",
                                  headers={'content-type': 'application/json'},
                                  data=payload2)

        payload3 = json.dumps({"review_id": 1, "action": '1'})
        response_actual = self.desktop_client.patch("/api/v1/review_feature/1",
                                                    headers={'content-type': 'application/json'},
                                                    data=payload3)
        self.assertRaises(ProcessingException)
        self.logout()
        self.refresh_db()

    #####REVIEW FEATURE SHOP OWNER##########

    def test_review_feature_first_time_by_shop_owner(self):
        self.login(self.shop_owner_user.email, self.shop_owner_password)
        payload = json.dumps({"review_id": 1})
        response_actual = self.desktop_client.post("/api/v1/review_feature",
                                                   headers={'content-type': 'application/json'},
                                                   data=payload)
        self.assertEquals(response_actual.status_code, 201)
        self.logout()
        self.refresh_db()

    def test_review_unfeature_by_shop_owner(self):
        self.login(self.shop_owner_user.email, self.shop_owner_password)
        payload1 = json.dumps({"review_id": 1})
        self.desktop_client.post("/api/v1/review_feature",
                                 headers={'content-type': 'application/json'},
                                 data=payload1)

        payload2 = json.dumps({"review_id": 1, "action": '0'})
        response_actual = self.desktop_client.patch("/api/v1/review_feature/1",
                                                    headers={'content-type': 'application/json'},
                                                    data=payload2)
        response_json_dict = json.loads(response_actual.data)
        self.assertEquals(response_json_dict["action"], 0)
        self.logout()
        self.refresh_db()

    def test_review_feature_again_by_shop_owner(self):
        self.login(self.shop_owner_user.email, self.shop_owner_password)
        payload1 = json.dumps({"review_id": 1})
        self.desktop_client.post("/api/v1/review_feature",
                                 headers={'content-type': 'application/json'},
                                 data=payload1)

        payload2 = json.dumps({"review_id": 1, "action": '0'})
        self.desktop_client.patch("/api/v1/review_feature/1",
                                  headers={'content-type': 'application/json'},
                                  data=payload2)

        payload3 = json.dumps({"review_id": 1, "action": '1'})
        response_actual = self.desktop_client.patch("/api/v1/review_feature/1",
                                                    headers={'content-type': 'application/json'},
                                                    data=payload3)
        response_json_dict = json.loads(response_actual.data)
        self.assertEquals(response_json_dict["action"], 1)
        self.logout()
        self.refresh_db()

    ##################TEST ORDERS#####################


    def test_post_order_by_reviewer(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.desktop_client.post("/api/v1/order",
                                                   headers={'content-type': 'application/json'},
                                                   data="{}")
        self.assertRaises(ProcessingException)
        self.logout()

    def test_post_order_by_shop_owner(self):
        self.login(self.shop_owner_user.email, self.shop_owner_password)
        time = str(datetime.datetime.utcnow())
        payload = json.dumps({"shop_id": 2, "platform_order_id": '2',
                              "user_id": 2, "user_legacy_id": 2, "delivery_tracking_number": "1234",
                              "discount": "20%", "status": "PURCHASED",
                              "purchase_timestamp": time, "shipment_timestamp": time,
                              "to_notify_timestamp": time, "notification_timestamp": time})
        response_actual = self.desktop_client.post("/api/v1/order",
                                                   headers={'content-type': 'application/json'},
                                                   data=payload)
        self.assertEqual(response_actual.status_code, 201)
        response_json_dict = json.loads(response_actual.data)
        self.assertEqual(response_json_dict["shop_id"], 2)
        self.assertEqual(response_json_dict["platform_order_id"], '2')
        self.assertEqual(response_json_dict["user_id"], 2)
        self.assertEqual(response_json_dict["user_legacy_id"], 2)
        self.assertEqual(response_json_dict["discount"], "20%")
        self.assertEqual(response_json_dict["delivery_tracking_number"], "1234")
        self.assertEqual(response_json_dict["status"], "PURCHASED")
        self.logout()
        self.refresh_db()

    ###########TEST USER##############
    def test_get_users_not_logged_in(self):
        response_actual = self.desktop_client.get("/api/v1/user")
        self.assertEqual(response_actual.status_code, 200)

    def test_get_users_reviewer(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.desktop_client.get("/api/v1/user")
        self.assertEqual(response_actual.status_code, 200)
        self.logout()

    def test_get_users_by_admin(self):
        self.login(self.admin_user.email, self.admin_password)
        response_actual = self.desktop_client.get("/api/v1/user")
        self.assertEqual(response_actual.status_code, 200)
        self.logout()

    def test_get_users_by_admin_contents_not_empty(self):
        self.login(self.admin_user.email, self.admin_password)
        response_actual = self.desktop_client.get("/api/v1/user")
        response_json_dict = json.loads(response_actual.data)
        self.assertTrue(len(response_json_dict["objects"]) > 0)
        self.logout()

    def test_get_user_by_admin(self):
        self.login(self.admin_user.email, self.admin_password)
        response_actual = self.desktop_client.get("/api/v1/user/1")
        response_json_dict = json.loads(response_actual.data)
        self.assertEqual(response_json_dict["id"], 1)
        self.assertEqual(response_json_dict["name"], "Daniel Tsvetkov")
        self.assertEqual(response_json_dict["email"], "daniel@opinew.com")
        self.assertTrue(isinstance(response_json_dict["image_url"], unicode))
        self.logout()

    ############TEST NOTIFICATIONS############

    def test_get_notifications_not_logged_in(self):
        response_actual = self.desktop_client.get("/api/v1/notification")
        self.assertEqual(response_actual.status_code, 401)
        self.assertRaises(ProcessingException)

    def test_get_notifications_by_reviewer_status_code(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.desktop_client.get("/api/v1/notification")
        self.assertEqual(response_actual.status_code, 200)
        self.logout()

    def test_get_notifications_by_reviewer_empty(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        response_actual = self.desktop_client.get("/api/v1/notification")
        response_json_dict = json.loads(response_actual.data)
        self.assertEqual(len(response_json_dict["objects"]), 0)
        self.logout()

    def test_get_notifications_by_reviewer_not_empty(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        notification1 = Notification(content="Hello sir!", url="www.your-notification.com",
                                     user_id=2)
        notification2 = Notification(content="Hello sir!", url="www.your-notification.com",
                                     user_id=1)
        db.session.add(notification1)
        db.session.add(notification2)
        db.session.commit()
        response_actual = self.desktop_client.get("/api/v1/notification")
        response_json_dict = json.loads(response_actual.data)
        self.assertEqual(len(response_json_dict["objects"]), 1)
        self.refresh_db()
        self.logout()

    def test_get_notifications_content_by_reviewer(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        notification = Notification(content="Hello sir!", url="www.your-notification.com",
                                    user_id=2)
        db.session.add(notification)
        db.session.commit()
        response_actual = self.desktop_client.get("/api/v1/notification")
        response_json_dict = json.loads(response_actual.data)
        self.assertEqual(response_json_dict["objects"][0]["id"], 1)
        self.assertEqual(response_json_dict["objects"][0]["content"], "Hello sir!")
        self.assertEqual(response_json_dict["objects"][0]["url"], "www.your-notification.com")
        self.assertEqual(response_json_dict["objects"][0]["user_id"], 2)
        self.refresh_db()
        self.logout()

    def test_get_somebody_elses_notification_by_reviewer(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        notification = Notification(content="Hello sir!", url="www.your-notification.com",
                                    user_id=1)
        db.session.add(notification)
        db.session.commit()
        response_actual = self.desktop_client.get("/api/v1/notification/1")
        self.assertEqual(response_actual.status_code, 401)
        self.assertRaises(ProcessingException)
        self.refresh_db()
        self.logout()

    def test_read_notification_by_reviewer(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        notification = Notification(content="Hello sir!", url="www.your-notification.com",
                                    user_id=2)
        db.session.add(notification)
        db.session.commit()

        payload = json.dumps({})
        response_actual = self.desktop_client.patch("/api/v1/notification/1",
                                                    headers={'content-type': 'application/json'},
                                                    data=payload)
        response_json_dict = json.loads(response_actual.data)
        self.assertEqual(response_actual.status_code, 200)
        self.assertEqual(response_json_dict["is_read"], True)
        self.refresh_db()
        self.logout()

    def test_read_somebody_elses_notification_by_reviewer(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        notification = Notification(content="Hello sir!", url="www.your-notification.com",
                                    user_id=1)
        db.session.add(notification)
        db.session.commit()

        payload = json.dumps({})
        response_actual = self.desktop_client.patch("/api/v1/notification/1",
                                                    headers={'content-type': 'application/json'},
                                                    data=payload)
        self.assertEqual(response_actual.status_code, 401)
        self.assertRaises(ProcessingException)

        self.refresh_db()
        self.logout()

    #################TEST SHOP###############

    def test_create_shop_by_reviewer(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        payload = json.dumps({})
        response_actual = self.desktop_client.post("/api/v1/shop",
                                                   headers={'content-type': 'application/json'},
                                                   data=payload)
        self.assertEqual(response_actual.status_code, 401)
        self.assertRaises(ProcessingException)
        self.refresh_db()
        self.logout()

    def test_create_shop_by_shop_owner(self):
        self.login(self.shop_owner_user.email, self.shop_owner_password)
        payload = json.dumps({})
        response_actual = self.desktop_client.post("/api/v1/shop",
                                                   headers={'content-type': 'application/json'},
                                                   data=payload)
        response_json_dict = json.loads(response_actual.data)
        self.assertEqual(response_actual.status_code, 201)
        self.assertEqual(response_json_dict["owner_id"], self.shop_owner_user.id)
        self.refresh_db()
        self.logout()

    def test_edit_shop_by_reviewer(self):
        self.login(self.reviewer_user.email, self.reviewer_password)
        payload = json.dumps({"description": "changed"})
        response_actual = self.desktop_client.patch("/api/v1/shop/2",
                                                    headers={'content-type': 'application/json'},
                                                    data=payload)
        self.assertEqual(response_actual.status_code, 401)
        self.assertRaises(ProcessingException)
        self.refresh_db()
        self.logout()

    def test_edit_shop_by_shop_owner(self):
        self.login(self.shop_owner_user.email, self.shop_owner_password)
        payload = json.dumps({"description": "changed"})
        response_actual = self.desktop_client.patch("/api/v1/shop/2",
                                                    headers={'content-type': 'application/json'},
                                                    data=payload)
        response_json_dict = json.loads(response_actual.data)
        self.assertEqual(response_actual.status_code, 200)
        self.assertEqual(response_json_dict["description"], "changed")
        self.refresh_db()
        self.logout()

    def test_edit_somebody_elses_shop_by_shop_owner(self):
        self.login(self.shop_owner_user.email, self.shop_owner_password)
        payload = json.dumps({"description": "changed"})
        response_actual = self.desktop_client.patch("/api/v1/shop/3",
                                                    headers={'content-type': 'application/json'},
                                                    data=payload)
        self.assertEqual(response_actual.status_code, 401)
        self.assertRaises(ProcessingException)
        self.refresh_db()
        self.logout()


    ###########ReviewRequest############


