#!venv/bin/python
import os
import sys
from webapp import models, db, create_app
from config import Constants

# populate tables
arguments = sys.argv
if not len(sys.argv) == 2 or arguments[1] not in ['db_dev', 'db_prod']:
    print "USAGE: ./repopulate.py db_dev|db_prod"
    exit(1)
option = arguments[1]
app = create_app(option)

db.init_app(app)

try:
    os.remove('/tmp/ecommerce_api.db')
except OSError:
    pass

app.app_context().push()
db.create_all()

shopify_platform = models.Platform(name='shopify')
db.session.add(shopify_platform)

user1 = models.User(name="Peter Reviewer", role=Constants.REVIEWER_ROLE, email='peter@example.com', password='password')
db.session.add(user1)

rachel = models.User(name="Rachel McMillan", role=Constants.SHOP_OWNER_ROLE, email='rachel@rachel-mcmillan.com', password='password')
db.session.add(rachel)

SHOP_URL = 'fake.myshopify.com'
rachels_shop = models.Shop(label='Fake shop', domain=SHOP_URL, platform=shopify_platform)
rachels_shop.owner = rachel
db.session.add(rachels_shop)
db.session.commit()
