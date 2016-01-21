from webapp import create_app, models, db
from pprint import pprint
import datetime

SHOP_ID = 5
PRODUCT_ID = 55

app = create_app('production')
app.app_context().push()

shop = models.Shop.query.filter_by(id=SHOP_ID).first()
products = models.Product.query.filter_by(shop=shop).all()

product_orders = [(p.id, len(p.orders.all())) for p in products]
most_sold_products = sorted(product_orders, key=lambda k: k[1], reverse=True)
# product 55 has most orders - 82

for product in most_sold_products[:10]:
    product55 = models.Product.query.filter_by(id=product[0]).first()
    orders55ts = sorted([o.purchase_timestamp for o in product55.orders.all()])
    data_x = []
    data_y = []
    s = 0

    print "Product %s: %s" % (product[0], len(orders55ts))

    for o in orders55ts:
        s += 1
        data_x.append((o - orders55ts[0]).days)
        data_y.append(s)

    # from scipy import stats
    # slope, intercept, r_value, p_value, std_err = stats.linregress(data_x, data_y)
    #
    # # import numpy
    # # slope, intercept = numpy.polyfit(data_x, data_y, 1)
    # now = datetime.datetime.utcnow()
    #
    # X = (now - orders55ts[0]).days
    # print "at day %s (%s): %s (r^2: %s, sterr: %s)" % (X, orders55ts[0] + datetime.timedelta(days=X), slope*X + intercept, r_value**2, std_err)
    # print '---'
