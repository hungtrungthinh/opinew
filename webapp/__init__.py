import logging
from flaskopinewext import FlaskOpinewExt
from flask import g, request, redirect, flash, session
from flask_admin import Admin, BaseView
from flask_wtf.csrf import CsrfProtect
from flask.ext.admin import AdminIndexView, expose
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.migrate import Migrate
from flask.ext.security import Security, SQLAlchemyUserDatastore, login_required, roles_required
from flask.ext.restless import APIManager
from flask.ext.uploads import IMAGES, UploadSet, configure_uploads, patch_request_class
from flask.ext.gravatar import Gravatar
from flask.ext.babel import Babel
from flask.ext.assets import Environment, Bundle
from flask_resize import Resize
from flask_mail import Mail
from werkzeug.exceptions import default_exceptions
from config import config_factory, Constants
from assets import strings
from flask.ext.compress import Compress
from logging.handlers import SMTPHandler
from logging import Formatter
from user_agents import parse
from werkzeug.datastructures import ImmutableTypeConversionDict
from exceptions import RequirementException


class MyHomeView(AdminIndexView):
    @expose('/')
    @login_required
    @roles_required(Constants.ADMIN_ROLE)
    def index(self):
        from webapp import models
        users = models.User.query.order_by(models.User.id).all()
        return self.render('admin/index.html',
                           users=users)


class AnalyticsView(BaseView):
    @expose('/')
    @login_required
    @roles_required(Constants.ADMIN_ROLE)
    def stats(self):
        from webapp import models
        from async import celery_async
        customers=models.Customer.query.all()
        return self.render('admin/analytics.html',
                           customers=customers)


class EmailRenderView(BaseView):
    @expose('/')
    @login_required
    @roles_required(Constants.ADMIN_ROLE)
    def stats(self):
        from webapp import models
        template_names = Constants.HTML_TO_INLINE_FILENAMES
        return self.render('admin/email_render.html', template_names=template_names)


csrf = CsrfProtect()
db = SQLAlchemy()
babel = Babel()
migrate = Migrate()

mail = Mail()
admin = Admin(template_mode='bootstrap3', index_view=MyHomeView())
admin.add_view(AnalyticsView(name="Analytics", endpoint='analytics'))
admin.add_view(EmailRenderView(name="Email Renders", endpoint='email-renders'))
security = Security()
api_manager = APIManager()
compress = Compress()
gravatar = Gravatar(size=42, rating='g', default='mm', force_default=False, use_ssl=True, base_url=None)

user_images = UploadSet('userimages', IMAGES)
review_images = UploadSet('reviewimages', IMAGES)
shop_images = UploadSet('shopimages', IMAGES)

resize = Resize()
assets = Environment()
js_assets = Bundle('js/main.js', filters='rjsmin', output='js/main.min.js')
css_assets = Bundle('css/global.css', filters='cssmin', output='css/global.min.css')


def create_app(option):
    app = FlaskOpinewExt(__name__)
    config = config_factory.get(option)
    app.config.from_object(config)

    from common import create_jinja_filters, random_pwd, verify_initialization

    create_jinja_filters(app)
    from webapp.client import client
    from webapp.media import media

    app.register_blueprint(client)
    app.register_blueprint(media, url_prefix=Constants.MEDIA_URL_PREFIX)

    compress.init_app(app)
    gravatar.init_app(app)
    resize.init_app(app)
    db.init_app(app)
    admin.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    babel.init_app(app)
    from models import User, Role
    from webapp.forms import ExtendedRegisterForm

    assets.init_app(app)
    assets.register('js_all', js_assets)
    assets.register('css_all', css_assets)

    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security.init_app(app, user_datastore, confirm_register_form=ExtendedRegisterForm)
    with app.app_context():
        from providers import database, payment

        if not app.testing:
            verify_initialization()

        if app.testing:
            from async import tasks
        api_manager.init_app(app, flask_sqlalchemy_db=db)

        @app.before_request
        def before_request():
            # hack to allow browsers who don't set 3rd party cookies
            x_session = request.headers.get('X-Session')
            if x_session:
                rc = dict(request.cookies)
                rc['session'] = x_session
                request.cookies = ImmutableTypeConversionDict(rc)
                # refresh session
                refreshed_csrf_token = app.session_interface.open_session(app, request).get('csrf_token')
                session['csrf_token'] = refreshed_csrf_token
            user_agent = parse(request.user_agent.string)
            g.mobile = False
            if user_agent.is_mobile or user_agent.is_tablet:
                g.mobile = True
            g.constants = Constants
            g.config = app.config
            g.mode = app.config.get('MODE')
            g.response_context = []
            g.s = strings
            g.payment = payment.StripeAPI()
            g.db = database.OpinewSQLAlchemyFacade()

        @app.after_request
        def redirect_if_next(response_class):
            if request.endpoint == 'static':
                response_class.headers['Access-Control-Allow-Origin'] = '*'
            payload = request.args if request.method == 'GET' else request.form
            if 'api_next' in payload:
                if not response_class.status_code == 200:
                    flash(response_class.data)
                    return redirect(request.referrer)
                return redirect(payload.get('api_next'))
            return response_class

    # register here CSRF so that the before_request is executed after the hack above
    csrf.init_app(app)
    patch_request_class(app, Constants.MAX_FILE_SIZE)

    from webapp.common import make_json_error

    for code in default_exceptions.iterkeys():
        app.error_handler_spec[None][code] = make_json_error

    configure_uploads(app, (user_images, review_images, shop_images, ))
    admins = [email for name, email in config.ADMINS]

    if not (app.debug or app.testing):
        mail_handler = SMTPHandler(app.config.get('MAIL_SERVER'),
                                   'server-error@opinew.com',
                                   admins,
                                   'Your Application Failed',
                                   credentials=(app.config.get('MAIL_USERNAME'), app.config.get('MAIL_PASSWORD')),
                                   secure=())
        mail_handler.setLevel(logging.ERROR)
        mail_handler.setFormatter(Formatter('''
Time        : %(asctime)s
Location    : %(pathname)s:%(lineno)d
Module      : %(module)s
Function    : %(funcName)s

%(message)s'''))
        app.logger.addHandler(mail_handler)

    return app
