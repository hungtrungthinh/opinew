import json
from flask import url_for
from freezegun import freeze_time
from unittest import TestCase
from webapp import create_app, db
from webapp.models import User, Role
from repopulate import Repopulate
from config import Constants


class TestFlaskApplication(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app('testing')
        cls.client = cls.app.test_client()
        cls.app.app_context().push()
        db.create_all()
        Repopulate().populate_db('test')

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()

    def login(self, email, password):
        return self.client.post('/login', data=dict(
            email=email,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)


class TestClientBlueprint(TestFlaskApplication):
    def test_urls(self):
        for rule in self.app.url_map.iter_rules():
            # Filter out rules we can't navigate to in a browser
            # and rules that require parameters
            if "GET" in rule.methods:
                if rule.endpoint in ['static', 'admin.static', 'security.reset_password']:
                    continue
                url = url_for(rule.endpoint, **(rule.defaults or {}))
                self.client.get(url, follow_redirects=True)

    def test_get_index(self):
        response_actual = self.client.get("/")
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h1>Opinew - Photo Product Reviews</h1>' in response_actual.data)

    def test_get_reviews(self):
        response_actual = self.client.get("/reviews")
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Business owner?' in response_actual.data)
        self.assertTrue('<b>Opinew shop</b>' in response_actual.data)


class TestClientBlueprintAdminViews(TestFlaskApplication):
    def setUp(self):
        admin_role = Role.query.filter_by(name=Constants.ADMIN_ROLE).first()
        admin_user = User.query.filter(User.roles.contains(admin_role)).first()
        r = self.login(admin_user.email, 'Opinu@m4d4f4k4!')

    def tearDown(self):
        self.logout()

    def test_access_admin_home(self):
        response_actual = self.client.get("/admin/", follow_redirects=True)
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h1>Welcome to admin panel</h1>' in response_actual.data)


class TestClientBlueprintReviewerViews(TestFlaskApplication):
    def setUp(self):
        reviewer_role = Role.query.filter_by(name=Constants.REVIEWER_ROLE).first()
        reviewer_user = User.query.filter(User.roles.contains(reviewer_role)).first()
        r = self.login(reviewer_user.email, reviewer_user.password)

    def tearDown(self):
        self.logout()

    def test_render_add_review_no_product(self):
        response_actual = self.client.get("/add_review")
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('Select product' in response_actual.data)

    def test_render_add_review_product_1(self):
        response_actual = self.client.get("/add_review", query_string={"product_id": 1})
        self.assertEquals(response_actual.status_code, 200)
        self.assertTrue('<h1>Review Ear rings' in response_actual.data)


class TestAPIBlueprintReviewerCalls(TestFlaskApplication):
    def setUp(self):
        reviewer_role = Role.query.filter_by(name=Constants.REVIEWER_ROLE).first()
        reviewer_user = User.query.filter(User.roles.contains(reviewer_role)).first()
        r = self.login(reviewer_user.email, reviewer_user.password)

    def tearDown(self):
        self.logout()

    @freeze_time("2015-03-14")
    def test_api_post_review(self):
        self.maxDiff = None
        body_payload = "fdsa"
        payload = json.dumps({"shop_product_id": "1", "star_rating": "4", "body": body_payload})
        response_actual = self.client.post("/api/v1/review",
                                           headers={'content-type': 'application/json'},
                                           data=payload)
        self.assertEquals(response_actual.status_code, 201)
        self.assertTrue(body_payload in response_actual.data)
