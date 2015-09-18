import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Constants(object):
    NOTIFICATION_AFTER_DELIVERY_SECONDS = 2 * 24 * 60 * 60  # 2 days
    TEMP_PWD_LEN = 5


class Config(object):
    OPINEW_API_SERVER = 'http://162.13.140.76'
    SECRET_KEY = 'fheiy3rihiewui4439845ty89o'

    UPLOADED_USERPHOTOS_DEST = os.path.join(basedir, 'media', 'user')
    UPLOADED_USERPHOTOS_URL = '/media/user/'

    UPLOADED_REVIEWPHOTOS_DEST = os.path.join(basedir, 'media', 'review')
    UPLOADED_REVIEWPHOTOS_URL = '/media/review/'

    DEFAULT_PROFILE_PICTURE = 'default_user.png'


class ConfigTest(Config):
    TESTING = True
    SERVER_NAME = 'localhost:5000'
    SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/ecommerce_api_test.db'


class ConfigDev(Config):
    DEBUG = True
    OPINEW_API_SERVER = 'http://opinew_api.local:5000'
    SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/ecommerce_api.db'


class ConfigProd(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:////home/opinew_server/db/ecommerce_api_test.db'


config_factory = {
    'db_prod': ConfigProd,
    'db_dev': ConfigDev,
    'test': ConfigTest,
    'dev': ConfigDev,
    'production': ConfigProd
}
