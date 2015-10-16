import os
import sensitive

basedir = os.path.abspath(os.path.dirname(__file__))


class Constants(object):
    DEFAULT_PROFILE_PICTURE = 'default_user.png'
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
    API_V1_URL_PREFIX = '/api/v1'
    AUTH_URL_PREFIX = '/auth'
    MEDIA_URL_PREFIX = '/media'
    NOTIFICATION_AFTER_DELIVERY_SECONDS = 2 * 24 * 60 * 60  # 2 days
    TEMP_PWD_LEN = 5
    SHOP_OWNER_ROLE = 'SHOP_OWNER'
    REVIEWER_ROLE = 'REVIEWER'
    ADMIN_ROLE = 'ADMIN'
    REVIEWS_PER_PAGE = 10
    NOTIFICATIONS_INITIAL = 20


class Config(object):
    # TODO: when we completely decouple with flask-mail remove these three
    SMTP_SERVER = "smtpout.europe.secureserver.net"
    EMAIL_ADDRESS = "team@opinew.com"
    EMAIL_PASSWORD = sensitive.EMAIL_PASSWORD

    MAIL_SERVER = "smtpout.europe.secureserver.net"
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USERNAME = "team@opinew.com"
    MAIL_PASSWORD = sensitive.EMAIL_PASSWORD

    OPINEW_API_SERVER = 'https://opinew.com'
    SECRET_KEY = sensitive.SECRET_KEY

    UPLOADED_USERPHOTOS_DEST = os.path.join(basedir, 'media', 'user')
    UPLOADED_USERPHOTOS_URL = '/media/user/'

    UPLOADED_REVIEWPHOTOS_DEST = os.path.join(basedir, 'media', 'review')
    UPLOADED_REVIEWPHOTOS_URL = '/media/review/'

    SHOPIFY_APP_API_KEY = sensitive.SHOPIFY_APP_API_KEY
    SHOPIFY_APP_SECRET = sensitive.SHOPIFY_APP_SECRET
    SHOPIFY_APP_SCOPES = 'read_products,read_orders,read_fulfillments'

    SECURITY_PASSWORD_HASH = 'bcrypt'
    SECURITY_PASSWORD_SALT = sensitive.SECURITY_PASSWORD_SALT
    SECURITY_CONFIRMABLE = False
    SECURITY_TRACKABLE = True
    SECURITY_REGISTERABLE = True
    SECURITY_RECOVERABLE  = True
    SECURITY_CHANGEABLE = True


class ConfigTest(Config):
    MODE = 'testing'
    WTF_CSRF_ENABLED = False
    TESTING = True
    SERVER_NAME = 'localhost:5000'
    SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/ecommerce_api_test.db'

    UPLOADED_USERPHOTOS_DEST  = os.path.join('tmp', 'media', 'user')
    UPLOADED_REVIEWPHOTOS_DEST = os.path.join('tmp', 'media', 'review')


class ConfigDev(Config):
    MODE = 'development'
    DEBUG = True
    OPINEW_API_SERVER = 'http://localhost:5000'
    SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/ecommerce_api.db'


class ConfigProd(Config):
    MODE = 'production'
    SQLALCHEMY_DATABASE_URI = 'sqlite:////home/opinew_server/db/ecommerce_api.db'


config_factory = {
    'dummy': Config,
    'db_prod': ConfigProd,
    'db_dev': ConfigDev,
    'testing': ConfigTest,
    'development': ConfigDev,
    'production': ConfigProd
}
