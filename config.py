# -*- coding: utf-8 -*-
import os
import sensitive
from celery.schedules import crontab

basedir = os.path.abspath(os.path.dirname(__file__))


class Constants(object):
    META_DEFAULT_TITLE = "Opinew"
    META_DEFAULT_DESCRIPTION = "Opinew is the photo review platform for the new generation"
    META_DEFAULT_PRERENDER = "/reviews"

    MODE_DEVELOPMENT = 'development'
    MODE_PRODUCTION = 'production'
    MODE_TESTING = 'testing'
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
    YOUTUBE_WATCH_LINK = 'https://www.youtube.com/watch?v='
    YOUTUBE_SHORT_LINK = 'https://youtu.be/'
    YOUTUBE_EMBED_URL = 'https://www.youtube.com/embed/{youtube_video_id}'

    ORDER_STATUS_PURCHASED = 'PURCHASED'
    ORDER_STATUS_SHIPPED = 'SHIPPED'
    ORDER_STATUS_DELIVERED = 'DELIVERED'
    ORDER_STATUS_NOTIFIED = 'NOTIFIED'
    ORDER_STATUS_REVIEWED = 'REVIEWED'

    ORDER_STATUS_FAILED = 'FAILED'
    ORDER_STATUS_STALLED = 'STALLED'
    ORDER_STATUS_LEGACY = 'LEGACY'
    ORDER_STATUS_REVIEW_CANCELED = 'REVIEW_CANCELED'

    ORDER_ACTION_NOTIFY = 'NOTIFY'
    ORDER_ACTION_DELETE = 'DELETE'
    ORDER_ACTION_CANCEL_REVIEW = 'CANCEL_REVIEW'

    DIFF_SHIPMENT_DELIVERY = 5
    DIFF_DELIVERY_NOTIFY = 3
    DIFF_PURCHASE_STALL = 14


class Config(object):
    ADMINS = [("Daniel Tsvetkov", 'danieltcv@gmail.com'),
              ("Tomasz Sadowski", 'tomsz.sadowski@gmail.com')]

    # Double assignment because of selery
    EMAIL_HOST = MAIL_SERVER = "smtpout.europe.secureserver.net"
    SERVER_EMAIL = 'celery-error@opinew.com'  # celery
    MAIL_DEFAULT_SENDER = 'team@opinew.com'
    EMAIL_PORT = MAIL_PORT = 465
    EMAIL_USE_SSL = MAIL_USE_SSL = True
    EMAIL_HOST_USER = MAIL_USERNAME = "team@opinew.com"
    EMAIL_HOST_PASSWORD = MAIL_PASSWORD = sensitive.EMAIL_PASSWORD

    OPINEW_API_SERVER = 'https://opinew.com'
    SECRET_KEY = sensitive.SECRET_KEY
    PROPAGATE_EXCEPTIONS = True

    UPLOADED_USERIMAGES_DEST = os.path.join(basedir, 'media', 'user')
    UPLOADED_USERIMAGES_URL = '/media/user/'

    UPLOADED_REVIEWIMAGES_DEST = os.path.join(basedir, 'media', 'review')
    UPLOADED_REVIEWIMAGES_URL = '/media/review/'

    UPLOADED_SHOPIMAGES_DEST = os.path.join(basedir, 'media', 'shop')
    UPLOADED_SHOPIMAGES_URL = '/media/shop/'

    SHOPIFY_APP_API_KEY = sensitive.SHOPIFY_APP_API_KEY
    SHOPIFY_APP_SECRET = sensitive.SHOPIFY_APP_SECRET
    SHOPIFY_APP_SCOPES = 'read_products,read_orders,read_fulfillments'

    SECURITY_PASSWORD_HASH = 'bcrypt'
    SECURITY_PASSWORD_SALT = sensitive.SECURITY_PASSWORD_SALT
    SECURITY_SEND_REGISTER_EMAIL = False
    SECURITY_CONFIRMABLE = True
    SECURITY_TRACKABLE = True
    SECURITY_REGISTERABLE = True
    SECURITY_RECOVERABLE = True
    SECURITY_CHANGEABLE = True
    SECURITY_POST_REGISTER_VIEW = '/confirm'
    SECURITY_POST_CHANGE_VIEW = '/post-change'

    CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672//'
    CELERY_RESULT_BACKEND = 'amqp://guest:guest@localhost:5672//'
    CELERY_SEND_TASK_ERROR_EMAILS = True

    STRIPE_PUBLISHABLE_API_KEY = 'pk_test_YFZO6qldIQDkOcOQz88TudE3'
    STRIPE_API_KEY = sensitive.STRIPE_TEST_API_KEY

    FB_APP_ID = '1636982329849520'
    FB_APP_SECRET = sensitive.FB_APP_SECRET

    TWITTER_API_KEY = 'EeuhsnB1e4uwC6MSN5YIF7eGZ'
    TWITTER_API_SECRET = sensitive.TWITTER_API_SECRET
    TWITTER_APP_ACCESS_TOKEN = '3013280003-rZBNIbqXigzTaJyhb9u0I46VzwpKeY4cheFDsXs'
    TWITTER_APP_ACCESS_SECRET = sensitive.TWITTER_APP_ACCESS_SECRET

    GIPHY_API_KEY = sensitive.GIPHY_API_KEY

    CELERYBEAT_SCHEDULE = {
        # Every day at 00:00
        'update_orders': {
            'task': 'async.tasks.update_orders',
            'schedule': crontab(minute=13, hour=18),
            'args': (),
        },
    }


class ConfigTest(Config):
    MODE = Constants.MODE_TESTING
    WTF_CSRF_ENABLED = False
    TESTING = True
    SERVER_NAME = 'localhost:5000'
    OPINEW_API_SERVER = 'http://localhost:5000'
    SQLALCHEMY_DATABASE_URI = 'postgresql://opinew_user:%s@localhost:5432/opinew_test' % sensitive.ADMIN_PASSWORD

    UPLOADED_USERIMAGES_DEST = os.path.join('tmp', 'media', 'user')
    UPLOADED_REVIEWIMAGES_DEST = os.path.join('tmp', 'media', 'review')
    UPLOADED_SHOPIMAGES_DEST = os.path.join('tmp', 'media', 'shop')


class ConfigDev(Config):
    MODE = Constants.MODE_DEVELOPMENT
    SERVER_NAME = 'localhost:5000'
    DEBUG = True
    OPINEW_API_SERVER = 'http://localhost:5000'
    SQLALCHEMY_DATABASE_URI = 'postgresql://opinew_user:%s@localhost:5432/opinew' % sensitive.ADMIN_PASSWORD


class ConfigProd(Config):
    MODE = Constants.MODE_PRODUCTION
    SERVER_NAME = 'opinew.com'
    SESSION_COOKIE_HTTPONLY = False
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://opinew_user:%s@localhost:5432/opinew' % sensitive.ADMIN_PASSWORD
    STRIPE_PUBLISHABLE_API_KEY = 'pk_test_YFZO6qldIQDkOcOQz88TudE3'  # TODO: 'pk_live_m5uUEwvggTYcIdrpqYSHZoab'
    STRIPE_API_KEY = sensitive.STRIPE_API_KEY


config_factory = {
    'dummy': Config,
    'db_prod': ConfigProd,
    'db_dev': ConfigDev,
    'testing': ConfigTest,
    'development': ConfigDev,
    'production': ConfigProd
}
