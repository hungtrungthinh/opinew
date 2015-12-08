import os
import requests
from unittest import TestCase
import webapp
from webapp import db, common
from webapp.models import User, Role
from config import Constants, basedir
import sensitive
from repopulate import import_tables
import threading
from flask import Flask, request, jsonify

app = webapp.create_app('testing')

class TestFlaskApplication(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app
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
        db.engine.dialect.supports_sane_multi_rowcount = False

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
        cls.shop_owner_user = User.query.filter_by(id=3).first()
        assert cls.shop_owner_user.has_role(shop_owner_role)
        cls.shop_owner_password = sensitive.TEST_SHOP_OWNER_PASSWORD

        cls.vserver = VirtualServerManager()
        cls.vserver.start()

    def setUp(self):
        self.admin_user = User.query.filter_by(id=1).first()
        self.reviewer_user = User.query.filter_by(id=2).first()
        self.shop_owner_user = User.query.filter_by(id=3).first()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()
        cls.vserver.stop()

    def login(self, email, password):
        return self.desktop_client.post('/login', data=dict(
            email=email,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.desktop_client.get('/logout', follow_redirects=True)

    @classmethod
    def refresh_db(cls):
        db.session.remove()
        db.drop_all()
        db.create_all()
        db.engine.dialect.supports_sane_multi_rowcount = False

        db_dir = os.path.join(basedir, 'install', 'db', cls.app.config.get('MODE'))
        import_tables(db, db_dir)

class TestModel(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app

        cls.app.app_context().push()
        db.session.remove()
        db.drop_all()
        db.create_all()
        db.engine.dialect.supports_sane_multi_rowcount = False

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()

class VirtualServerManager(object):
    def __init__(self):
        self.vserver_thread = None

    def start(self):
        # Start a virtual server on port 5678
        from webapp.vshopify import vshopify
        from webapp.vstripe import vstripe

        vserver_app = Flask(__name__)
        vserver_app.register_blueprint(vshopify, url_prefix='/vshopify')
        vserver_app.register_blueprint(vstripe, url_prefix='/vstripe')

        def shutdown_server():
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                raise RuntimeError('Not running with the Werkzeug Server')
            func()

        @vserver_app.errorhandler(404)
        def page_not_found(e):
            return jsonify({'method': request.method, 'path': request.path}), 404

        @vserver_app.route('/shutdown', methods=['POST'])
        def shutdown():
            shutdown_server()
            return 'Server shutting down...'

        self.vserver_thread = threading.Thread(target=vserver_app.run, kwargs=dict(port=Constants.VIRTUAL_SERVER_PORT, use_reloader=False, debug=True))
        self.vserver_thread.start()

    def stop(self):
        requests.post(Constants.VIRTUAL_SERVER + '/shutdown')
        self.vserver_thread.join()

