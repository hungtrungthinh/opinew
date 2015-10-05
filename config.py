import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Constants(object):
    NOTIFICATION_AFTER_DELIVERY_SECONDS = 2 * 24 * 60 * 60  # 2 days
    TEMP_PWD_LEN = 5
    SHOP_OWNER_ROLE = 'SHOP_OWNER'
    REVIEWER_ROLE = 'REVIEWER'


class Config(object):
    SMTP_SERVER = "smtp.example.com"
    EMAIL_ADDRESS = "admin@example.com"
    EMAIL_PASSWORD = "password"

    OPINEW_API_SERVER = 'https://opinew.com'
    SECRET_KEY = 'fheiy3rihiewui4439845ty89o'

    UPLOADED_USERPHOTOS_DEST = os.path.join(basedir, 'media', 'user')
    UPLOADED_USERPHOTOS_URL = '/media/user/'

    UPLOADED_REVIEWPHOTOS_DEST = os.path.join(basedir, 'media', 'review')
    UPLOADED_REVIEWPHOTOS_URL = '/media/review/'

    DEFAULT_PROFILE_PICTURE = 'default_user.png'

    SHOPIFY_APP_API_KEY = '7260cb38253b9adc4af0c90eb622f4ce'
    SHOPIFY_APP_SECRET = '4aff6d82da2174ec13167f149ff7ee50'
    SHOPIFY_APP_SCOPES = 'read_products,read_orders,read_fulfillments'


class ConfigTest(Config):
    MODE = 'testing'
    TESTING = True
    SERVER_NAME = 'localhost:5000'
    SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/ecommerce_api_test.db'


class ConfigDev(Config):
    MODE = 'development'
    DEBUG = True
    OPINEW_API_SERVER = 'http://opinew.com:5000'
    SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/ecommerce_api.db'


class ConfigProd(Config):
    MODE = 'production'
    SQLALCHEMY_DATABASE_URI = 'sqlite:////home/opinew_server/db/ecommerce_api.db'


config_factory = {
    'db_prod': ConfigProd,
    'db_dev': ConfigDev,
    'testing': ConfigTest,
    'development': ConfigDev,
    'production': ConfigProd
}
