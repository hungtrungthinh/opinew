import os
from webapp import models, db, create_app
from csv_utf_support import CSVUnicodeReader
from fuzzywuzzy import fuzz

basedir = os.path.abspath(os.path.dirname(__file__))
file_path = os.path.join(basedir, '..', 'tests', 'test_files', 'twitter_beauty_kitchen.csv')

app = create_app('db_dev')
db.init_app(app)
app.app_context().push()

bk_shop = models.Shop.query.filter_by(name="Beauty Kitchen").first()
products = models.Product.query.filter_by(shop_id=bk_shop.id).all()

product_names = [product.name.lower() for product in products]

with open(file_path) as f:
    csv_reader = CSVUnicodeReader(f, lineterminator='\n')
    status_product_ratios = {}
    for i, line in enumerate(csv_reader):
        status_text = line[0].lower()
        status_product_ratios[i] = {
            'status_text': status_text,
            'ratios': []
            }
        ratios = []
        for product_text in product_names:
            ratio = fuzz.ratio(product_text, status_text)
            rd = {
                'product_text': product_text,
                'ratio': ratio
            }
            if ratio > 30:
                ratios.append(rd)
        ratios = sorted(ratios, key=lambda k: k['ratio'], reverse=True)
        status_product_ratios[i]['ratios'] = ratios
    print status_product_ratios

