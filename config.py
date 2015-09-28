import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Constants(object):
    NOTIFICATION_AFTER_DELIVERY_SECONDS = 2 * 24 * 60 * 60  # 2 days
    TEMP_PWD_LEN = 5
    SHOP_OWNER_ROLE = 'SHOP_OWNER'
    REVIEWER_ROLE = 'REVIEWER'


class Config(object):
    OPINEW_API_SERVER = 'http://162.13.140.76:5000'  #'http://109.151.240.95:5000'
    SECRET_KEY = 'fheiy3rihiewui4439845ty89o'

    UPLOADED_USERPHOTOS_DEST = os.path.join(basedir, 'media', 'user')
    UPLOADED_USERPHOTOS_URL = '/media/user/'

    UPLOADED_REVIEWPHOTOS_DEST = os.path.join(basedir, 'media', 'review')
    UPLOADED_REVIEWPHOTOS_URL = '/media/review/'

    DEFAULT_PROFILE_PICTURE = 'default_user.png'

    SHOPIFY_APP_API_KEY = '7260cb38253b9adc4af0c90eb622f4ce'
    SHOPIFY_APP_SECRET = '4aff6d82da2174ec13167f149ff7ee50'
    SHOPIFY_APP_SCOPES = 'read_products,read_orders,read_fulfillments'
    SHOPIFY_OAUTH_CALLBACK = '%s/oauth/callback' % OPINEW_API_SERVER


class ConfigTest(Config):
    TESTING = True
    SERVER_NAME = 'localhost:5000'
    SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/ecommerce_api_test.db'


class ConfigDev(Config):
    DEBUG = True
    OPINEW_API_SERVER = 'http://opinew_api.local:5000'
    SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/ecommerce_api.db'


class ConfigProd(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:////home/opinew_server/db/ecommerce_api.db'


config_factory = {
    'db_prod': ConfigProd,
    'db_dev': ConfigDev,
    'test': ConfigTest,
    'dev': ConfigDev,
    'production': ConfigProd
}
