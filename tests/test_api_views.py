import json
from unittest import TestCase
from webapp import create_app, db
from webapp.models import User


class TestAPI(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app('testing')
        cls.client = cls.app.test_client()
        cls.app.app_context().push()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()


class TestAuthenticateAPI(TestAPI):
    @classmethod
    def setUpClass(cls):
        cls.USER_EMAIL = 'test@example.com'
        cls.USER_PWD = 'testing'

        super(TestAuthenticateAPI, cls).setUpClass()
        user = User(email=cls.USER_EMAIL, password=cls.USER_PWD)
        db.session.add(user)
        db.session.commit()

    def test_authentication_no_email(self):
        response_actual = self.client.post("/api/authenticate", data={'password': self.USER_PWD})
        response_expected = {'error': 'email parameter is required'}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 400)

    def test_authentication_no_password(self):
        response_actual = self.client.post("/api/authenticate", data={'email': self.USER_EMAIL})
        response_expected = {'error': 'password parameter is required'}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 400)

    def test_non_existing_user_authentication(self):
        response_actual = self.client.post("/api/authenticate", data={'email': 'nope',
                                                                      'password': self.USER_PWD})
        response_expected = {'error': 'User with email nope does not exist.'}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 400)

    def test_user_authentication_wrong_password(self):
        response_actual = self.client.post("/api/authenticate", data={'email': self.USER_EMAIL,
                                                                      'password': 'incorrect'})
        response_expected = {'error': 'Wrong password.'}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 400)

    def test_correct_authentication(self):
        response_actual = self.client.post("/api/authenticate", data={'email': self.USER_EMAIL,
                                                                      'password': self.USER_PWD})
        response_expected = {}
        self.assertEquals(json.loads(response_actual.data), response_expected)
        self.assertEquals(response_actual.status_code, 200)
