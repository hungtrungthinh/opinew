import os
from importers import magento
from webapp import create_app, db, models

app = create_app('db_dev')
app.app_context().push()

basedir = os.path.abspath(os.path.dirname(__file__))
beauty_kitchen_shop = models.Shop.query.filter_by(name="Beauty Kitchen").first()
BK_SHOP_URL = 'http://www.beautykitchen.co.uk/'
magento_products = magento.products_import(os.path.join(basedir, 'test_files', 'beauty_kitchen.csv'))
BK_IMAGE_BASE = 'http://www.beautykitchen.co.uk/media/catalog/product/cache/1/image/363x/040ec09b1e35df139433887a97daa66f'
for p in magento_products:
    if not p.get('name', None):
        continue
    product = models.Product(name=p.get('name'),
                             active=True if p.get('status', 0) == u'1' else False,
                             short_description=p.get('short_description'),
                             product_type='Beauty Products',
                             category=p.get('_category'),
                             image_url="%s%s" % (BK_IMAGE_BASE, p.get('image')),
                             shop=beauty_kitchen_shop,
                             url="%s%s" % (BK_SHOP_URL, p.get('url_path')),
                             platform_product_id=p.get('sku'))
    db.session.add(product)