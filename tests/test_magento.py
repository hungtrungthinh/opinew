from providers import magento_api
from webapp import db
from webapp.models import Shop
from tests.framework import TestFlaskApplication

class TestMagentoUpdateOrders(TestFlaskApplication):
    def test_init(self):
        shop = Shop()
        db.session.add(shop)
        db.session.commit()
        magento_api.init(shop)
