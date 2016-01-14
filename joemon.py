from webapp import create_app, models, db
from pprint import pprint

app = create_app('production')
app.app_context().push()

s = models.Shop.query.filter_by(id=5).first()
stats = []
for p in s.products:
    product_orders = len(p.orders.all())
    product_reviews = len(p.reviews)
    product_review_requests = len(p.review_requests)
    data = {
        'orders': product_orders,
        'review_requests': product_review_requests
    }
    stats.append(data)

pprint(sorted(stats, key=lambda k: k['review_requests']))