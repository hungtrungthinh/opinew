import os
from flask.ext.uploads import IMAGES, UploadSet

basedir = os.path.abspath(os.path.dirname(__file__))


class Constants(object):
    NOTIFICATION_AFTER_DELIVERY_SECONDS = 2 * 24 * 60 * 60  # 2 days
    TEMP_PWD_LEN = 5


class Config(object):
    SECRET_KEY = 'fheiy3rihiewui4439845ty89o'
    SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/ecommerce_api.db'

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


config_factory = {
    'db': Config,
    'test': ConfigTest,
    'dev': ConfigDev
}
