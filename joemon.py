from webapp import create_app, models, db
from pprint import pprint

SHOP_ID = 5
PRODUCT_ID = 161

app = create_app('production')
app.app_context().push()

shop = models.Shop.query.filter_by(id=SHOP_ID).first()
products = models.Product.query.filter_by(shop=shop).all()

product_orders = [(p.id, len(p.orders.all())) for p in products]
pprint(sorted(product_orders, key=lambda k: k[1]))
# product 55 has most orders - 82

product55 = models.Product.query.filter_by(id=PRODUCT_ID).first()
orders55ts = sorted([o.purchase_timestamp for o in product55.orders.all()])
data_x = []
data_y = []
s = 0

for o in orders55ts:
    s += 1
    data_x.append(o)
    data_y.append(s)


import matplotlib.pyplot as plt

pprint(data_x)
pprint(data_y)

plt.plot(data_x, data_y)
plt.gcf().autofmt_xdate()
plt.savefig('figs/%s_%s' % (SHOP_ID, PRODUCT_ID))
