#!venv/bin/python
import os
import sys
from webapp import models, db, create_app

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

shop_role = models.Role(name='SHOP')
reviewer_role = models.Role(name='REVIEWER')
db.session.add(shop_role)
db.session.add(reviewer_role)

shop_access = models.Access(url='shop_admin')
db.session.add(shop_access)

shop_role.access_whitelist.append(shop_access)

user1 = models.User(name="Daniel Tsvetkov", email='danieltcv@gmail.com', password='password')
user1.role = reviewer_role
db.session.add(user1)

shop_user = models.User(name="Shop Owner", email='owner@onlineshop.com', password='password')
shop_user.role = shop_role
db.session.add(shop_user)

product1 = models.Product(label='Skirt')
product2 = models.Product(label='Tshirt')
db.session.add(product1)
db.session.add(product2)

good_tag = models.Tag(label='Good', connotation=100)
bad_tag = models.Tag(label='Bad', connotation=-100)

product1.tags.append(good_tag)
product1.tags.append(bad_tag)
product2.tags.append(good_tag)
product2.tags.append(bad_tag)

SHOP_URL = 'http://localhost:5001/'
shop = models.Shop(label='My Online Shop', url=SHOP_URL, owner=shop_user, shipment_time_in_days=1)
db.session.add(shop)

db.session.add(models.ShopProduct(shop=shop, product=product1, url="%s/product/%s" % (SHOP_URL, product1.id)))
db.session.add(models.ShopProduct(shop=shop, product=product2, url="%s/product/%s" % (SHOP_URL, product2.id)))

db.session.commit()
