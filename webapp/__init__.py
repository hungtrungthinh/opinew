from flask import Flask
from flask_httpauth import HTTPBasicAuth
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.uploads import IMAGES, UploadSet, configure_uploads
from werkzeug.exceptions import default_exceptions


from config import config_factory

auth = HTTPBasicAuth()
login_manager = LoginManager()
db = SQLAlchemy()

user_photos = UploadSet('userphotos', IMAGES)
review_photos = UploadSet('reviewphotos', IMAGES)

def create_app(option):
    app = Flask(__name__)
    config = config_factory.get(option)
    app.config.from_object(config)
    from common import create_jinja_filters
    create_jinja_filters(app)
    from webapp.api import api
    from webapp.client import client
    app.register_blueprint(client)
    app.register_blueprint(api, url_prefix='/api')

    db.init_app(app)
    login_manager.init_app(app)

    from webapp.common import make_json_error
    for code in default_exceptions.iterkeys():
        app.error_handler_spec[None][code] = make_json_error

    configure_uploads(app, (user_photos, review_photos,))

    return app
