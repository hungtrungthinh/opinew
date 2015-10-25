import os
import sensitive

basedir = os.path.abspath(os.path.dirname(__file__))


class Constants(object):
    DEFAULT_PROFILE_PICTURE = 'default_user.png'
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
    API_V1_URL_PREFIX = '/api/v1'
    MEDIA_URL_PREFIX = '/media'
    NOTIFICATION_AFTER_DELIVERY_SECONDS = 2 * 24 * 60 * 60  # 2 days
    TEMP_PWD_LEN = 5
    SHOP_OWNER_ROLE = 'SHOP_OWNER'
    REVIEWER_ROLE = 'REVIEWER'
    ADMIN_ROLE = 'ADMIN'
    REVIEWS_PER_PAGE = 10
    NOTIFICATIONS_INITIAL = 20
    CURRENCY = "gbp"


class Config(object):
    MAIL_SERVER = "smtpout.europe.secureserver.net"
    MAIL_DEFAULT_SENDER = 'noreply@opinew.com'
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

    CELERY_BROKER_URL='amqp://guest:guest@localhost:5672//'
    CELERY_RESULT_BACKEND = 'amqp://guest:guest@localhost:5672//'

    STRIPE_API_KEY = sensitive.STRIPE_TEST_API_KEY

    FB_APP_ID = '1636982329849520'
    FB_APP_SECRET = sensitive.FB_APP_SECRET

    TWITTER_API_KEY = 'EeuhsnB1e4uwC6MSN5YIF7eGZ'
    TWITTER_API_SECRET = sensitive.TWITTER_API_SECRET
    TWITTER_APP_ACCESS_TOKEN = '3013280003-rZBNIbqXigzTaJyhb9u0I46VzwpKeY4cheFDsXs'
    TWITTER_APP_ACCESS_SECRET = sensitive.TWITTER_APP_ACCESS_SECRET

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
    STRIPE_API_KEY = sensitive.STRIPE_API_KEY


config_factory = {
    'dummy': Config,
    'db_prod': ConfigProd,
    'db_dev': ConfigDev,
    'testing': ConfigTest,
    'development': ConfigDev,
    'production': ConfigProd
}
