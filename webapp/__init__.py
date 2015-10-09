from flask import Flask,g
from flask_admin import Admin
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.security import Security
from flask.ext.restless import APIManager
from flask.ext.uploads import IMAGES, UploadSet, configure_uploads, patch_request_class
from flask.ext.gravatar import Gravatar
from flask_mail import Mail
from werkzeug.exceptions import default_exceptions
from config import config_factory, Constants
from flask.ext.compress import Compress

db = SQLAlchemy()
mail = Mail()
admin = Admin()
security = Security()
api_manager = APIManager()
compress = Compress()
gravatar = Gravatar(size=100, rating='g', default='retro', force_default=False, use_ssl=False, base_url=None)

user_photos = UploadSet('userphotos', IMAGES)
review_photos = UploadSet('reviewphotos', IMAGES)


def create_app(option):
    app = Flask(__name__)
    config = config_factory.get(option)
    app.config.from_object(config)
    from common import create_jinja_filters

    create_jinja_filters(app)
    from webapp.auth import auth
    from webapp.api import api
    from webapp.client import client
    from webapp.media import media

    app.register_blueprint(client)
    app.register_blueprint(auth, url_prefix=Constants.AUTH_URL_PREFIX)
    app.register_blueprint(api, url_prefix=Constants.API_V1_URL_PREFIX)
    app.register_blueprint(media, url_prefix=Constants.MEDIA_URL_PREFIX)

    compress.init_app(app)
    gravatar.init_app(app)
    db.init_app(app)
    admin.init_app(app)
    security.init_app(app)
    mail.init_app(app)
    with app.app_context():
        api_manager.init_app(app, flask_sqlalchemy_db=db)

        @app.before_request
        def before_request():
            g.constants = Constants
            g.config = app.config
            g.mode = app.config.get('MODE')

    patch_request_class(app, Constants.MAX_FILE_SIZE)

    from webapp.common import make_json_error

    for code in default_exceptions.iterkeys():
        app.error_handler_spec[None][code] = make_json_error

    configure_uploads(app, (user_photos, review_photos,))

    return app
