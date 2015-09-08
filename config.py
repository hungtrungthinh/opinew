import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Constants(object):
    NOTIFICATION_AFTER_DELIVERY_SECONDS = 2*24*60*60  # 2 days
    TEMP_PWD_LEN = 5

class Config(object):
    DEBUG = True
    SECRET_KEY = 'fheiy3rihiewui4439845ty89o'
    SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/ecommerce_api.db'

    UPLOADED_USERPHOTOS_DEST = os.path.join(basedir, 'webapp', 'media', 'user')
    UPLOADED_USERPHOTOS_URL = '/media/user/'

    UPLOADED_REVIEWPHOTOS_DEST = os.path.join(basedir, 'webapp', 'media', 'review')
    UPLOADED_REVIEWPHOTOS_URL = '/media/review/'

    DEFAULT_PROFILE_PICTURE = 'default_user.png'
