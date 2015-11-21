from flaskopinewext import FlaskOpinewExt
from flask import g, request, redirect, flash, render_template
from flask_admin import Admin
from flask_wtf.csrf import CsrfProtect
from flask.ext.admin import AdminIndexView, expose
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.migrate import Migrate
from flask.ext.security import Security, SQLAlchemyUserDatastore, login_required, roles_required
from flask.ext.restless import APIManager
from flask.ext.uploads import IMAGES, UploadSet, configure_uploads, patch_request_class
from flask.ext.gravatar import Gravatar
from flask_mail import Mail
from werkzeug.exceptions import default_exceptions
from config import config_factory, Constants
from flask.ext.compress import Compress
import logging
from logging.handlers import SMTPHandler
from logging import Formatter


class MyHomeView(AdminIndexView):
    @expose('/')
    @login_required
    @roles_required(Constants.ADMIN_ROLE)
    def index(self):
        return self.render('admin/index.html')


csrf = CsrfProtect()
db = SQLAlchemy()
migrate = Migrate()

mail = Mail()
admin = Admin(template_mode='bootstrap3', index_view=MyHomeView())
security = Security()
api_manager = APIManager()
compress = Compress()
gravatar = Gravatar(size=100, rating='g', default='mm', force_default=False, use_ssl=True, base_url=None)

user_images = UploadSet('userimages', IMAGES)
review_images = UploadSet('reviewimages', IMAGES)


def create_app(option):
    app = FlaskOpinewExt(__name__)
    config = config_factory.get(option)
    app.config.from_object(config)
    from common import create_jinja_filters, random_pwd

    create_jinja_filters(app)
    from webapp.api import api
    from webapp.client import client
    from webapp.media import media

    app.register_blueprint(client)
    app.register_blueprint(api, url_prefix=Constants.API_V1_URL_PREFIX)
    app.register_blueprint(media, url_prefix=Constants.MEDIA_URL_PREFIX)

    csrf.init_app(app)
    compress.init_app(app)
    gravatar.init_app(app)
    db.init_app(app)
    admin.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    from models import User, Role
    from webapp.forms import ExtendedRegisterForm

    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security.init_app(app, user_datastore, confirm_register_form=ExtendedRegisterForm)
    with app.app_context():
        api_manager.init_app(app, flask_sqlalchemy_db=db)

        @app.before_request
        def before_request():
            g.mobile = False
            if request.headers.get('mobile'):
                g.mobile = True
            g.constants = Constants
            g.config = app.config
            g.mode = app.config.get('MODE')

        @app.after_request
        def redirect_if_next(response_class):
            payload = request.args if request.method == 'GET' else request.form
            if 'api_next' in payload:
                if not response_class.status_code == 200:
                    flash(response_class.data)
                    return redirect(request.referrer)
                return redirect(payload.get('api_next'))
            return response_class

    patch_request_class(app, Constants.MAX_FILE_SIZE)

    from webapp.common import make_json_error

    for code in default_exceptions.iterkeys():
        app.error_handler_spec[None][code] = make_json_error

    configure_uploads(app, (user_images, review_images,))

    ADMINS = ['danieltcv@gmail.com']
    if not app.debug:
        @app.errorhandler(500)
        def internal_error(exception):
            app.logger.error(exception)
            return render_template('errors/500.html'), 500

        mail_handler = SMTPHandler(app.config.get('MAIL_SERVER'),
                                   'server-error@opinew.com',
                                   ADMINS,
                                   'YourApplication Failed',
                                   credentials=(app.config.get('MAIL_USERNAME'), app.config.get('MAIL_PASSWORD')))
        mail_handler.setLevel(logging.ERROR)
        mail_handler.setFormatter(Formatter('''
        Message type:       %(levelname)s
        Location:           %(pathname)s:%(lineno)d
        Module:             %(module)s
        Function:           %(funcName)s
        Time:               %(asctime)s

        %(message)s
        '''))
        app.logger.addHandler(mail_handler)

    return app
