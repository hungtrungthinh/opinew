import datetime
from providers import magento_api
from webapp import db
from webapp.models import Shop, Product, Order, User, Customer, UserLegacy
from tests.framework import TestFlaskApplication, expect_mail
from tests import testing_constants
from config import Constants
from freezegun import freeze_time


class TestMagentoUpdateOrders(TestFlaskApplication):
    @freeze_time(testing_constants.MAGENTO_JUST_SHIPPED_FROZEN_TS)
    @expect_mail
    def test_init(self):
        user_shop_owner = User(email=testing_constants.NEW_USER_EMAIL)
        Customer(user=user_shop_owner)
        shop = Shop(domain=testing_constants.MAGENTO_SHOP_DOMAIN, name=testing_constants.MAGENTO_SHOP_NAME)
        shop.owner = user_shop_owner
        db.session.add(shop)
        db.session.commit()

        shop_id = shop.id

        magento_api.init(shop)

        # TEST
        self.assertEquals(len(self.outbox), 1)
        self.assertEquals(len(self.outbox[0].send_to), 1)
        self.assertEquals(self.outbox[0].send_to.pop(), testing_constants.MAGENTO_ORDER_1_EMAIL)
        self.assertEquals(self.outbox[0].subject,
                          Constants.DEFAULT_REVIEW_SUBJECT % (testing_constants.MAGENTO_ORDER_1_NAME.split()[0],
                                                              testing_constants.MAGENTO_SHOP_NAME))
        self.assertTrue(testing_constants.MAGENTO_ORDER_1_NAME.split()[0] in self.outbox[0].body)
        self.assertTrue(testing_constants.MAGENTO_PRODUCT_0_NAME in self.outbox[0].body)
        self.assertTrue(testing_constants.MAGENTO_PRODUCT_1_NAME in self.outbox[0].body)
        self.assertTrue(testing_constants.MAGENTO_SHOP_NAME in self.outbox[0].body)

        products = Product.query.filter_by(shop_id=shop_id).all()
        self.assertEqual(len(products), 3)
        self.assertEqual(products[0].platform_product_id, testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID)
        self.assertEqual(products[0].name, testing_constants.MAGENTO_PRODUCT_0_NAME)
        self.assertEqual(products[0].short_description, testing_constants.MAGENTO_PRODUCT_0_DESCRIPTION)
        self.assertTrue(products[0].active)
        self.assertEqual(len(products[0].urls), 2)
        self.assertFalse(products[0].urls[0].is_regex)
        self.assertEqual(products[0].urls[0].url,
                         '%s/%s' % (testing_constants.MAGENTO_SHOP_DOMAIN, testing_constants.MAGENTO_PRODUCT_0_URL_KEY))
        self.assertTrue(products[0].urls[1].is_regex)
        self.assertEqual(products[0].urls[1].url, '%s/(.)*%s' % (
        testing_constants.MAGENTO_SHOP_DOMAIN, testing_constants.MAGENTO_PRODUCT_0_URL_KEY))

        self.assertEqual(products[1].platform_product_id, testing_constants.MAGENTO_PRODUCT_1_PLATFORM_PRODUCT_ID)
        self.assertEqual(products[1].name, testing_constants.MAGENTO_PRODUCT_1_NAME)
        self.assertEqual(products[1].short_description, testing_constants.MAGENTO_PRODUCT_1_DESCRIPTION)
        self.assertTrue(products[1].active)
        self.assertEqual(len(products[1].urls), 2)
        self.assertFalse(products[1].urls[0].is_regex)
        self.assertEqual(products[1].urls[0].url,
                         '%s/%s' % (testing_constants.MAGENTO_SHOP_DOMAIN, testing_constants.MAGENTO_PRODUCT_1_URL_KEY))
        self.assertTrue(products[1].urls[1].is_regex)
        self.assertEqual(products[1].urls[1].url, '%s/(.)*%s' % (
        testing_constants.MAGENTO_SHOP_DOMAIN, testing_constants.MAGENTO_PRODUCT_1_URL_KEY))

        self.assertEqual(products[2].platform_product_id, testing_constants.MAGENTO_PRODUCT_2_PLATFORM_PRODUCT_ID)
        self.assertEqual(products[2].name, testing_constants.MAGENTO_PRODUCT_2_NAME)
        self.assertEqual(products[2].short_description, testing_constants.MAGENTO_PRODUCT_2_DESCRIPTION)
        self.assertFalse(products[2].active)
        self.assertEqual(len(products[2].urls), 2)
        self.assertFalse(products[2].urls[0].is_regex)
        self.assertEqual(products[2].urls[0].url,
                         '%s/%s' % (testing_constants.MAGENTO_SHOP_DOMAIN, testing_constants.MAGENTO_PRODUCT_2_URL_KEY))
        self.assertTrue(products[2].urls[1].is_regex)
        self.assertEqual(products[2].urls[1].url, '%s/(.)*%s' % (
        testing_constants.MAGENTO_SHOP_DOMAIN, testing_constants.MAGENTO_PRODUCT_2_URL_KEY))

        orders = Order.query.filter_by(shop_id=shop_id).all()
        self.assertEqual(len(orders), 3)

        # tear down
        user = User.query.filter_by(email=testing_constants.NEW_USER_EMAIL).first()
        customer = user.customer[0]
        shop = Shop.query.filter_by(name=testing_constants.MAGENTO_SHOP_NAME).first()
        orders = Order.query.filter_by(shop_id=shop_id).all()
        self.assertEqual(orders[0].platform_order_id, testing_constants.MAGENTO_ORDER_0_PLATFORM_ORDER_ID)
        self.assertEqual(str(orders[0].purchase_timestamp), testing_constants.MAGENTO_ORDER_0_CREATED)
        self.assertIsNotNone(orders[0].user_legacy)
        self.assertEqual(orders[0].user_legacy.email, testing_constants.MAGENTO_ORDER_0_EMAIL)
        self.assertEqual(orders[0].user_legacy.name, testing_constants.MAGENTO_ORDER_0_NAME)
        self.assertEqual(len(orders[0].products), 1)

        self.assertEqual(orders[1].platform_order_id, testing_constants.MAGENTO_ORDER_1_PLATFORM_ORDER_ID)
        self.assertEqual(str(orders[1].purchase_timestamp), testing_constants.MAGENTO_ORDER_1_CREATED)
        self.assertIsNotNone(orders[1].user_legacy)
        self.assertEqual(orders[1].user_legacy.email, testing_constants.MAGENTO_ORDER_1_EMAIL)
        self.assertEqual(orders[1].user_legacy.name, testing_constants.MAGENTO_ORDER_1_NAME)
        self.assertEqual(len(orders[1].products), 2)

        self.assertEqual(orders[2].platform_order_id, testing_constants.MAGENTO_ORDER_2_PLATFORM_ORDER_ID)
        self.assertEqual(str(orders[2].purchase_timestamp), testing_constants.MAGENTO_ORDER_2_CREATED)
        self.assertIsNotNone(orders[2].user_legacy)
        self.assertEqual(orders[2].user_legacy.email, testing_constants.MAGENTO_ORDER_2_EMAIL)
        self.assertEqual(orders[2].user_legacy.name, testing_constants.MAGENTO_ORDER_2_NAME)
        self.assertEqual(len(orders[2].products), 0)

        for product in shop.products:
            db.session.delete(product)
        db.session.delete(user)
        db.session.delete(customer)
        db.session.delete(shop)
        db.session.delete(shop)
        for order in orders:
            for review_request in order.review_requests:
                db.session.delete(review_request)
            db.session.delete(order)
        db.session.commit()

    def test_fetch_new_and_updated_products_no_current_products(self):
        api = magento_api.API()
        new_and_updated = api.fetch_new_and_updated_products([])
        self.assertEquals(len(new_and_updated), 3)

        self.assertEquals(new_and_updated[0].platform_product_id,
                          testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID)
        self.assertEquals(new_and_updated[0].name, testing_constants.MAGENTO_PRODUCT_0_NAME)
        self.assertEquals(new_and_updated[0].urlkey, testing_constants.MAGENTO_PRODUCT_0_URL_KEY)
        self.assertEquals(new_and_updated[0].short_description, testing_constants.MAGENTO_PRODUCT_0_DESCRIPTION)
        self.assertTrue(new_and_updated[0].active)

        self.assertEquals(new_and_updated[1].platform_product_id,
                          testing_constants.MAGENTO_PRODUCT_1_PLATFORM_PRODUCT_ID)
        self.assertEquals(new_and_updated[1].name, testing_constants.MAGENTO_PRODUCT_1_NAME)
        self.assertEquals(new_and_updated[1].urlkey, testing_constants.MAGENTO_PRODUCT_1_URL_KEY)
        self.assertEquals(new_and_updated[1].short_description, testing_constants.MAGENTO_PRODUCT_1_DESCRIPTION)
        self.assertTrue(new_and_updated[1].active)

        self.assertEquals(new_and_updated[2].platform_product_id,
                          testing_constants.MAGENTO_PRODUCT_2_PLATFORM_PRODUCT_ID)
        self.assertEquals(new_and_updated[2].name, testing_constants.MAGENTO_PRODUCT_2_NAME)
        self.assertEquals(new_and_updated[2].urlkey, testing_constants.MAGENTO_PRODUCT_2_URL_KEY)
        self.assertEquals(new_and_updated[2].short_description, testing_constants.MAGENTO_PRODUCT_2_DESCRIPTION)
        self.assertFalse(new_and_updated[2].active)

    def test_fetch_new_and_updated_products_with_current_products_0(self):
        # setup with existing product 0
        shop = Shop()
        product = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID,
                          name=testing_constants.MAGENTO_PRODUCT_0_NAME,
                          active=True,
                          short_description=testing_constants.MAGENTO_PRODUCT_0_DESCRIPTION)
        shop.products.append(product)
        db.session.add(shop)
        db.session.commit()

        # Fetch
        api = magento_api.API()
        current_shop_products = Product.query.filter_by(shop_id=shop.id).all()
        new_and_updated = api.fetch_new_and_updated_products(current_shop_products)

        # Test
        self.assertEquals(len(new_and_updated), 2)

        self.assertEquals(new_and_updated[0].platform_product_id,
                          testing_constants.MAGENTO_PRODUCT_1_PLATFORM_PRODUCT_ID)
        self.assertEquals(new_and_updated[0].name, testing_constants.MAGENTO_PRODUCT_1_NAME)
        self.assertEquals(new_and_updated[0].urlkey, testing_constants.MAGENTO_PRODUCT_1_URL_KEY)
        self.assertEquals(new_and_updated[0].short_description, testing_constants.MAGENTO_PRODUCT_1_DESCRIPTION)
        self.assertTrue(new_and_updated[0].active)

        self.assertEquals(new_and_updated[1].platform_product_id,
                          testing_constants.MAGENTO_PRODUCT_2_PLATFORM_PRODUCT_ID)
        self.assertEquals(new_and_updated[1].name, testing_constants.MAGENTO_PRODUCT_2_NAME)
        self.assertEquals(new_and_updated[1].urlkey, testing_constants.MAGENTO_PRODUCT_2_URL_KEY)
        self.assertEquals(new_and_updated[1].short_description, testing_constants.MAGENTO_PRODUCT_2_DESCRIPTION)
        self.assertFalse(new_and_updated[1].active)

        # tear down
        db.session.delete(shop)
        db.session.delete(product)
        db.session.commit()

    def test_fetch_new_and_updated_no_new_or_updated(self):
        # setup with existing product 0, 1,2
        shop = Shop()
        product0 = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID,
                           name=testing_constants.MAGENTO_PRODUCT_0_NAME,
                           active=True,
                           short_description=testing_constants.MAGENTO_PRODUCT_0_DESCRIPTION)

        product1 = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_1_PLATFORM_PRODUCT_ID,
                           name=testing_constants.MAGENTO_PRODUCT_1_NAME,
                           active=True,
                           short_description=testing_constants.MAGENTO_PRODUCT_1_DESCRIPTION)

        product2 = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_2_PLATFORM_PRODUCT_ID,
                           name=testing_constants.MAGENTO_PRODUCT_2_NAME,
                           active=False,
                           short_description=testing_constants.MAGENTO_PRODUCT_2_DESCRIPTION)
        shop.products.append(product0)
        shop.products.append(product1)
        shop.products.append(product2)
        db.session.add(shop)
        db.session.commit()

        api = magento_api.API()
        current_shop_products = Product.query.filter_by(shop_id=shop.id).all()
        new_and_updated = api.fetch_new_and_updated_products(current_shop_products)

        # test
        self.assertEquals(len(new_and_updated), 0)

        # tear down
        db.session.delete(shop)
        db.session.delete(product0)
        db.session.delete(product1)
        db.session.delete(product2)
        db.session.commit()

    def test_fetch_new_and_updated_update_product_0_name_product_1_status_product_2_description(self):
        # setup with existing product 0, 1,2
        shop = Shop()
        product0 = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID,
                           name='dark side',  # change
                           active=True,
                           short_description=testing_constants.MAGENTO_PRODUCT_0_DESCRIPTION)

        product1 = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_1_PLATFORM_PRODUCT_ID,
                           name=testing_constants.MAGENTO_PRODUCT_1_NAME,
                           active=False,  # change
                           short_description=testing_constants.MAGENTO_PRODUCT_1_DESCRIPTION)

        product2 = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_2_PLATFORM_PRODUCT_ID,
                           name=testing_constants.MAGENTO_PRODUCT_2_NAME,
                           active=False,
                           short_description='oh oh')  # change
        shop.products.append(product0)
        shop.products.append(product1)
        shop.products.append(product2)
        db.session.add(shop)
        db.session.commit()

        api = magento_api.API()
        current_shop_products = Product.query.filter_by(shop_id=shop.id).all()
        new_and_updated = api.fetch_new_and_updated_products(current_shop_products)

        # test
        self.assertEquals(len(new_and_updated), 3)

        self.assertEquals(new_and_updated[0].platform_product_id,
                          testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID)
        self.assertEquals(new_and_updated[0].name, testing_constants.MAGENTO_PRODUCT_0_NAME)
        self.assertIsNone(getattr(new_and_updated[0], 'urlkey', None))
        self.assertEquals(new_and_updated[0].short_description, testing_constants.MAGENTO_PRODUCT_0_DESCRIPTION)
        self.assertTrue(new_and_updated[0].active)

        self.assertEquals(new_and_updated[1].platform_product_id,
                          testing_constants.MAGENTO_PRODUCT_1_PLATFORM_PRODUCT_ID)
        self.assertEquals(new_and_updated[1].name, testing_constants.MAGENTO_PRODUCT_1_NAME)
        self.assertIsNone(getattr(new_and_updated[1], 'urlkey', None))
        self.assertEquals(new_and_updated[1].short_description, testing_constants.MAGENTO_PRODUCT_1_DESCRIPTION)
        self.assertTrue(new_and_updated[1].active)

        self.assertEquals(new_and_updated[2].platform_product_id,
                          testing_constants.MAGENTO_PRODUCT_2_PLATFORM_PRODUCT_ID)
        self.assertEquals(new_and_updated[2].name, testing_constants.MAGENTO_PRODUCT_2_NAME)
        self.assertIsNone(getattr(new_and_updated[2], 'urlkey', None))
        self.assertEquals(new_and_updated[2].short_description, testing_constants.MAGENTO_PRODUCT_2_DESCRIPTION)
        self.assertFalse(new_and_updated[2].active)

        # tear down
        db.session.delete(shop)
        db.session.delete(product0)
        db.session.delete(product1)
        db.session.delete(product2)
        db.session.commit()

    def test_fetch_new_and_updated_update_product_0_new_product_2(self):
        # setup with existing product 0, 1,2
        shop = Shop()
        product0 = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID,
                           name='dark side',
                           active=True,
                           short_description=testing_constants.MAGENTO_PRODUCT_0_DESCRIPTION)

        product1 = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_1_PLATFORM_PRODUCT_ID,
                           name=testing_constants.MAGENTO_PRODUCT_1_NAME,
                           active=True,  # change
                           short_description=testing_constants.MAGENTO_PRODUCT_1_DESCRIPTION)

        shop.products.append(product0)
        shop.products.append(product1)
        db.session.add(shop)
        db.session.commit()

        api = magento_api.API()
        current_shop_products = Product.query.filter_by(shop_id=shop.id).all()
        new_and_updated = api.fetch_new_and_updated_products(current_shop_products)

        # test
        self.assertEquals(len(new_and_updated), 2)

        self.assertEquals(new_and_updated[0].platform_product_id,
                          testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID)
        self.assertEquals(new_and_updated[0].name, testing_constants.MAGENTO_PRODUCT_0_NAME)
        self.assertIsNone(getattr(new_and_updated[0], 'urlkey', None))
        self.assertEquals(new_and_updated[0].short_description, testing_constants.MAGENTO_PRODUCT_0_DESCRIPTION)
        self.assertTrue(new_and_updated[0].active)

        self.assertEquals(new_and_updated[1].platform_product_id,
                          testing_constants.MAGENTO_PRODUCT_2_PLATFORM_PRODUCT_ID)
        self.assertEquals(new_and_updated[1].name, testing_constants.MAGENTO_PRODUCT_2_NAME)
        self.assertEquals(new_and_updated[1].urlkey, testing_constants.MAGENTO_PRODUCT_2_URL_KEY)
        self.assertEquals(new_and_updated[1].short_description, testing_constants.MAGENTO_PRODUCT_2_DESCRIPTION)
        self.assertFalse(new_and_updated[1].active)

        # tear down
        db.session.delete(shop)
        db.session.delete(product0)
        db.session.delete(product1)
        db.session.commit()

    @freeze_time(testing_constants.MAGENTO_JUST_SHIPPED_FROZEN_TS)
    @expect_mail
    def test_fetch_new_and_updated_orders_no_current_orders(self):
        # setup with existing product 0, 1,2
        user_shop_owner = User(email=testing_constants.NEW_USER_EMAIL)
        Customer(user=user_shop_owner)
        shop = Shop(name=testing_constants.MAGENTO_SHOP_NAME)
        shop.owner = user_shop_owner
        product0 = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID,
                           name=testing_constants.MAGENTO_PRODUCT_0_NAME,
                           active=True,
                           short_description=testing_constants.MAGENTO_PRODUCT_0_DESCRIPTION)

        product1 = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_1_PLATFORM_PRODUCT_ID,
                           name=testing_constants.MAGENTO_PRODUCT_1_NAME,
                           active=True,
                           short_description=testing_constants.MAGENTO_PRODUCT_1_DESCRIPTION)

        product2 = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_2_PLATFORM_PRODUCT_ID,
                           name=testing_constants.MAGENTO_PRODUCT_2_NAME,
                           active=False,
                           short_description=testing_constants.MAGENTO_PRODUCT_2_DESCRIPTION)
        shop.products.append(product0)
        shop.products.append(product1)
        shop.products.append(product2)
        db.session.add(shop)
        db.session.commit()

        # test
        api = magento_api.API()
        new_and_updated = api.fetch_new_and_updated_orders([], shop)
        self.assertEquals(len(new_and_updated), 3)
        db.session.add_all(new_and_updated)
        db.session.commit()

        self.assertEquals(len(self.outbox), 1)
        self.assertEquals(len(self.outbox[0].send_to), 1)
        self.assertEquals(self.outbox[0].send_to.pop(), testing_constants.MAGENTO_ORDER_1_EMAIL)
        self.assertEquals(self.outbox[0].subject,
                          Constants.DEFAULT_REVIEW_SUBJECT % (testing_constants.MAGENTO_ORDER_1_NAME.split()[0],
                                                              testing_constants.MAGENTO_SHOP_NAME))
        self.assertTrue(testing_constants.MAGENTO_ORDER_1_NAME.split()[0] in self.outbox[0].body)
        self.assertTrue(testing_constants.MAGENTO_PRODUCT_0_NAME in self.outbox[0].body)
        self.assertTrue(testing_constants.MAGENTO_PRODUCT_1_NAME in self.outbox[0].body)
        self.assertTrue(testing_constants.MAGENTO_SHOP_NAME in self.outbox[0].body)

        self.assertEquals(new_and_updated[0].platform_order_id, testing_constants.MAGENTO_ORDER_0_PLATFORM_ORDER_ID)
        self.assertEquals(new_and_updated[0].status, Constants.ORDER_STATUS_PURCHASED)
        self.assertEquals(new_and_updated[0].purchase_timestamp,
                          datetime.datetime.strptime(testing_constants.MAGENTO_ORDER_0_CREATED, '%Y-%m-%d %H:%M:%S'))
        self.assertIsNone(new_and_updated[0].shipment_timestamp)
        self.assertEquals(len(new_and_updated[0].products), 1)
        self.assertIsNotNone(new_and_updated[0].products[0])
        self.assertEquals(new_and_updated[0].products[0].platform_product_id,
                          testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID)
        self.assertEquals(len(new_and_updated[0].tasks), 0)
        self.assertIsNotNone(new_and_updated[0].user_legacy)
        self.assertEquals(new_and_updated[0].user_legacy.email, testing_constants.MAGENTO_ORDER_0_EMAIL)
        self.assertEquals(new_and_updated[0].user_legacy.name, testing_constants.MAGENTO_ORDER_0_NAME)

        self.assertEquals(new_and_updated[1].platform_order_id, testing_constants.MAGENTO_ORDER_1_PLATFORM_ORDER_ID)
        self.assertEquals(new_and_updated[1].status, Constants.ORDER_STATUS_NOTIFIED)
        self.assertEquals(new_and_updated[1].purchase_timestamp,
                          datetime.datetime.strptime(testing_constants.MAGENTO_ORDER_1_CREATED, '%Y-%m-%d %H:%M:%S'))
        self.assertEquals(new_and_updated[1].shipment_timestamp,
                          datetime.datetime.strptime(testing_constants.MAGENTO_ORDER_1_SHIPPED, '%Y-%m-%d %H:%M:%S'))
        self.assertEquals(len(new_and_updated[1].products), 2)
        self.assertIsNotNone(new_and_updated[1].products[0])
        self.assertEquals(new_and_updated[1].products[0].platform_product_id,
                          testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID)
        self.assertIsNotNone(new_and_updated[1].products[1])
        self.assertEquals(new_and_updated[1].products[1].platform_product_id,
                          testing_constants.MAGENTO_PRODUCT_1_PLATFORM_PRODUCT_ID)
        self.assertEquals(len(new_and_updated[1].tasks), 2)
        self.assertEquals(new_and_updated[1].tasks[0].method, 'notify_for_review')
        self.assertEquals(str(new_and_updated[1].tasks[0].eta), '2015-12-19 12:00:00')
        self.assertEquals(new_and_updated[1].tasks[1].method, 'send_email')
        self.assertEquals(str(new_and_updated[1].tasks[1].eta), '2015-12-19 12:00:00')
        self.assertIsNotNone(new_and_updated[1].user_legacy)
        self.assertEquals(new_and_updated[1].user_legacy.email, testing_constants.MAGENTO_ORDER_1_EMAIL)
        self.assertEquals(new_and_updated[1].user_legacy.name, testing_constants.MAGENTO_ORDER_1_NAME)

        self.assertEquals(new_and_updated[2].platform_order_id, testing_constants.MAGENTO_ORDER_2_PLATFORM_ORDER_ID)
        self.assertEquals(new_and_updated[2].status, Constants.ORDER_STATUS_PURCHASED)
        self.assertEquals(new_and_updated[2].purchase_timestamp,
                          datetime.datetime.strptime(testing_constants.MAGENTO_ORDER_2_CREATED, '%Y-%m-%d %H:%M:%S'))
        self.assertIsNone(new_and_updated[2].shipment_timestamp)
        self.assertEquals(len(new_and_updated[2].products), 0)
        self.assertEquals(len(new_and_updated[2].tasks), 0)
        self.assertIsNotNone(new_and_updated[2].user_legacy)
        self.assertEquals(new_and_updated[2].user_legacy.email, testing_constants.MAGENTO_ORDER_2_EMAIL)
        self.assertEquals(new_and_updated[2].user_legacy.name, testing_constants.MAGENTO_ORDER_2_NAME)

        # tear down
        user = User.query.filter_by(email=testing_constants.NEW_USER_EMAIL).first()
        customer = user.customer[0]
        shop = Shop.query.filter_by(name=testing_constants.MAGENTO_SHOP_NAME).first()
        orders = Order.query.all()

        for product in shop.products:
            db.session.delete(product)
        db.session.delete(user)
        db.session.delete(customer)
        db.session.delete(shop)
        db.session.delete(shop)
        for order in orders:
            for review_request in order.review_requests:
                db.session.delete(review_request)
            db.session.delete(order)
        db.session.commit()

    @freeze_time(testing_constants.MAGENTO_JUST_SHIPPED_FROZEN_TS)
    @expect_mail
    def test_fetch_new_and_updated_orders_no_current_orders_users_already_exist(self):
        # setup with existing product 0, 1,2
        user_shop_owner = User(email=testing_constants.NEW_USER_EMAIL)
        Customer(user=user_shop_owner)
        shop = Shop(name=testing_constants.MAGENTO_SHOP_NAME)
        shop.owner = user_shop_owner
        product0 = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID,
                           name=testing_constants.MAGENTO_PRODUCT_0_NAME,
                           active=True,
                           short_description=testing_constants.MAGENTO_PRODUCT_0_DESCRIPTION)

        product1 = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_1_PLATFORM_PRODUCT_ID,
                           name=testing_constants.MAGENTO_PRODUCT_1_NAME,
                           active=True,
                           short_description=testing_constants.MAGENTO_PRODUCT_1_DESCRIPTION)

        product2 = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_2_PLATFORM_PRODUCT_ID,
                           name=testing_constants.MAGENTO_PRODUCT_2_NAME,
                           active=False,
                           short_description=testing_constants.MAGENTO_PRODUCT_2_DESCRIPTION)
        order0_user_legacy = UserLegacy(email=testing_constants.MAGENTO_ORDER_0_EMAIL,
                                        name=testing_constants.MAGENTO_ORDER_0_NAME)
        order1_user = User(email=testing_constants.MAGENTO_ORDER_1_EMAIL,
                                 name=testing_constants.MAGENTO_ORDER_1_NAME)
        order2_user = User(email=testing_constants.MAGENTO_ORDER_2_EMAIL,
                                 name=testing_constants.MAGENTO_ORDER_2_NAME)
        shop.products.append(product0)
        shop.products.append(product1)
        shop.products.append(product2)
        db.session.add(order0_user_legacy)
        db.session.add(order1_user)
        db.session.add(order2_user)
        db.session.add(shop)
        db.session.commit()

        # test
        api = magento_api.API()
        new_and_updated = api.fetch_new_and_updated_orders([], shop)
        self.assertEquals(len(new_and_updated), 3)
        db.session.add_all(new_and_updated)
        db.session.commit()

        self.assertEquals(len(self.outbox), 1)
        self.assertEquals(len(self.outbox[0].send_to), 1)
        self.assertEquals(self.outbox[0].send_to.pop(), testing_constants.MAGENTO_ORDER_1_EMAIL)
        self.assertEquals(self.outbox[0].subject,
                          Constants.DEFAULT_REVIEW_SUBJECT % (testing_constants.MAGENTO_ORDER_1_NAME.split()[0],
                                                              testing_constants.MAGENTO_SHOP_NAME))
        self.assertTrue(testing_constants.MAGENTO_ORDER_1_NAME.split()[0] in self.outbox[0].body)
        self.assertTrue(testing_constants.MAGENTO_PRODUCT_0_NAME in self.outbox[0].body)
        self.assertTrue(testing_constants.MAGENTO_PRODUCT_1_NAME in self.outbox[0].body)
        self.assertTrue(testing_constants.MAGENTO_SHOP_NAME in self.outbox[0].body)

        self.assertEquals(new_and_updated[0].platform_order_id, testing_constants.MAGENTO_ORDER_0_PLATFORM_ORDER_ID)
        self.assertEquals(new_and_updated[0].status, Constants.ORDER_STATUS_PURCHASED)
        self.assertEquals(new_and_updated[0].purchase_timestamp,
                          datetime.datetime.strptime(testing_constants.MAGENTO_ORDER_0_CREATED, '%Y-%m-%d %H:%M:%S'))
        self.assertIsNone(new_and_updated[0].shipment_timestamp)
        self.assertEquals(len(new_and_updated[0].products), 1)
        self.assertIsNotNone(new_and_updated[0].products[0])
        self.assertEquals(new_and_updated[0].products[0].platform_product_id,
                          testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID)
        self.assertEquals(len(new_and_updated[0].tasks), 0)
        self.assertIsNotNone(new_and_updated[0].user_legacy)
        self.assertEquals(new_and_updated[0].user_legacy.email, testing_constants.MAGENTO_ORDER_0_EMAIL)
        self.assertEquals(new_and_updated[0].user_legacy.name, testing_constants.MAGENTO_ORDER_0_NAME)

        self.assertEquals(new_and_updated[1].platform_order_id, testing_constants.MAGENTO_ORDER_1_PLATFORM_ORDER_ID)
        self.assertEquals(new_and_updated[1].status, Constants.ORDER_STATUS_NOTIFIED)
        self.assertEquals(new_and_updated[1].purchase_timestamp,
                          datetime.datetime.strptime(testing_constants.MAGENTO_ORDER_1_CREATED, '%Y-%m-%d %H:%M:%S'))
        self.assertEquals(new_and_updated[1].shipment_timestamp,
                          datetime.datetime.strptime(testing_constants.MAGENTO_ORDER_1_SHIPPED, '%Y-%m-%d %H:%M:%S'))
        self.assertEquals(len(new_and_updated[1].products), 2)
        self.assertIsNotNone(new_and_updated[1].products[0])
        self.assertEquals(new_and_updated[1].products[0].platform_product_id,
                          testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID)
        self.assertIsNotNone(new_and_updated[1].products[1])
        self.assertEquals(new_and_updated[1].products[1].platform_product_id,
                          testing_constants.MAGENTO_PRODUCT_1_PLATFORM_PRODUCT_ID)
        self.assertEquals(len(new_and_updated[1].tasks), 2)
        self.assertEquals(new_and_updated[1].tasks[0].method, 'notify_for_review')
        self.assertEquals(str(new_and_updated[1].tasks[0].eta), '2015-12-19 12:00:00')
        self.assertEquals(new_and_updated[1].tasks[1].method, 'send_email')
        self.assertEquals(str(new_and_updated[1].tasks[1].eta), '2015-12-19 12:00:00')
        self.assertIsNotNone(new_and_updated[1].user)
        self.assertEquals(new_and_updated[1].user.email, testing_constants.MAGENTO_ORDER_1_EMAIL)
        self.assertEquals(new_and_updated[1].user.name, testing_constants.MAGENTO_ORDER_1_NAME)

        self.assertEquals(new_and_updated[2].platform_order_id, testing_constants.MAGENTO_ORDER_2_PLATFORM_ORDER_ID)
        self.assertEquals(new_and_updated[2].status, Constants.ORDER_STATUS_PURCHASED)
        self.assertEquals(new_and_updated[2].purchase_timestamp,
                          datetime.datetime.strptime(testing_constants.MAGENTO_ORDER_2_CREATED, '%Y-%m-%d %H:%M:%S'))
        self.assertIsNone(new_and_updated[2].shipment_timestamp)
        self.assertEquals(len(new_and_updated[2].products), 0)
        self.assertEquals(len(new_and_updated[2].tasks), 0)
        self.assertIsNotNone(new_and_updated[2].user)
        self.assertEquals(new_and_updated[2].user.email, testing_constants.MAGENTO_ORDER_2_EMAIL)
        self.assertEquals(new_and_updated[2].user.name, testing_constants.MAGENTO_ORDER_2_NAME)

        # tear down
        user = User.query.filter_by(email=testing_constants.NEW_USER_EMAIL).first()
        customer = user.customer[0]
        shop = Shop.query.filter_by(name=testing_constants.MAGENTO_SHOP_NAME).first()
        orders = Order.query.all()

        for product in shop.products:
            db.session.delete(product)
        db.session.delete(user)
        db.session.delete(customer)
        db.session.delete(shop)
        db.session.delete(shop)
        for order in orders:
            for review_request in order.review_requests:
                db.session.delete(review_request)
            if order.user:
                db.session.delete(order.user)
            if order.user_legacy:
                db.session.delete(order.user_legacy)
            db.session.delete(order)
        db.session.commit()

    @freeze_time(testing_constants.MAGENTO_JUST_SHIPPED_FROZEN_TS)
    def test_fetch_new_and_updated_orders_already_exist(self):
        # setup with existing product 0,1,2
        user_shop_owner = User(email=testing_constants.NEW_USER_EMAIL)
        Customer(user=user_shop_owner)
        shop = Shop(name=testing_constants.MAGENTO_SHOP_NAME)
        shop.owner = user_shop_owner
        product0 = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID,
                           name=testing_constants.MAGENTO_PRODUCT_0_NAME,
                           active=True,
                           short_description=testing_constants.MAGENTO_PRODUCT_0_DESCRIPTION)

        product1 = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_1_PLATFORM_PRODUCT_ID,
                           name=testing_constants.MAGENTO_PRODUCT_1_NAME,
                           active=True,
                           short_description=testing_constants.MAGENTO_PRODUCT_1_DESCRIPTION)

        product2 = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_2_PLATFORM_PRODUCT_ID,
                           name=testing_constants.MAGENTO_PRODUCT_2_NAME,
                           active=False,
                           short_description=testing_constants.MAGENTO_PRODUCT_2_DESCRIPTION)

        order0_user_legacy = UserLegacy(email=testing_constants.MAGENTO_ORDER_0_EMAIL,
                                        name=testing_constants.MAGENTO_ORDER_0_NAME)
        order0 = Order(platform_order_id=testing_constants.MAGENTO_ORDER_0_PLATFORM_ORDER_ID,
                       status=Constants.ORDER_STATUS_PURCHASED,
                       purchase_timestamp=testing_constants.MAGENTO_ORDER_0_CREATED,
                       user_legacy=order0_user_legacy)
        order0.products.append(product0)

        order1_user_legacy = UserLegacy(email=testing_constants.MAGENTO_ORDER_1_EMAIL,
                                        name=testing_constants.MAGENTO_ORDER_1_NAME)
        order1 = Order(platform_order_id=testing_constants.MAGENTO_ORDER_1_PLATFORM_ORDER_ID,
                       status=Constants.ORDER_STATUS_NOTIFIED,
                       purchase_timestamp=testing_constants.MAGENTO_ORDER_1_CREATED,
                       shipment_timestamp=testing_constants.MAGENTO_ORDER_1_SHIPPED,
                       user_legacy=order1_user_legacy)
        order1.products.append(product0)
        order1.products.append(product1)

        order2_user_legacy = UserLegacy(email=testing_constants.MAGENTO_ORDER_2_EMAIL,
                                        name=testing_constants.MAGENTO_ORDER_2_NAME)
        order2 = Order(platform_order_id=testing_constants.MAGENTO_ORDER_2_PLATFORM_ORDER_ID,
                       status=Constants.ORDER_STATUS_PURCHASED,
                       purchase_timestamp=testing_constants.MAGENTO_ORDER_2_CREATED,
                       user_legacy=order2_user_legacy)

        shop.products.append(product0)
        shop.products.append(product1)
        shop.products.append(product2)
        shop.orders.append(order0)
        shop.orders.append(order1)
        shop.orders.append(order2)
        db.session.add(shop)
        db.session.commit()

        # test
        api = magento_api.API()
        current_orders = Order.query.filter_by(shop_id=shop.id).all()
        new_and_updated = api.fetch_new_and_updated_orders(current_orders, shop)
        self.assertEquals(len(new_and_updated), 0)

        # tear down
        user = User.query.filter_by(email=testing_constants.NEW_USER_EMAIL).first()
        customer = user.customer[0]
        shop = Shop.query.filter_by(name=testing_constants.MAGENTO_SHOP_NAME).first()
        orders = Order.query.all()

        for product in shop.products:
            db.session.delete(product)
        db.session.delete(user)
        db.session.delete(customer)
        db.session.delete(shop)
        db.session.delete(shop)
        for order in orders:
            for review_request in order.review_requests:
                db.session.delete(review_request)
            db.session.delete(order)
        db.session.commit()

    @freeze_time(testing_constants.MAGENTO_JUST_SHIPPED_FROZEN_TS)
    @expect_mail
    def test_fetch_new_and_updated_orders_already_exist_but_not_shipped(self):
        # setup with existing product 0,1,2
        user_shop_owner = User(email=testing_constants.NEW_USER_EMAIL)
        Customer(user=user_shop_owner)
        shop = Shop(name=testing_constants.MAGENTO_SHOP_NAME)
        shop.owner = user_shop_owner
        product0 = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID,
                           name=testing_constants.MAGENTO_PRODUCT_0_NAME,
                           active=True,
                           short_description=testing_constants.MAGENTO_PRODUCT_0_DESCRIPTION)

        product1 = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_1_PLATFORM_PRODUCT_ID,
                           name=testing_constants.MAGENTO_PRODUCT_1_NAME,
                           active=True,
                           short_description=testing_constants.MAGENTO_PRODUCT_1_DESCRIPTION)

        product2 = Product(platform_product_id=testing_constants.MAGENTO_PRODUCT_2_PLATFORM_PRODUCT_ID,
                           name=testing_constants.MAGENTO_PRODUCT_2_NAME,
                           active=False,
                           short_description=testing_constants.MAGENTO_PRODUCT_2_DESCRIPTION)

        order0_user_legacy = UserLegacy(email=testing_constants.MAGENTO_ORDER_0_EMAIL,
                                        name=testing_constants.MAGENTO_ORDER_0_NAME)
        order0 = Order(platform_order_id=testing_constants.MAGENTO_ORDER_0_PLATFORM_ORDER_ID,
                       status=Constants.ORDER_STATUS_PURCHASED,
                       purchase_timestamp=testing_constants.MAGENTO_ORDER_0_CREATED,
                       user_legacy=order0_user_legacy)
        order0.products.append(product0)

        order1_user_legacy = UserLegacy(email=testing_constants.MAGENTO_ORDER_1_EMAIL,
                                        name=testing_constants.MAGENTO_ORDER_1_NAME)
        order1 = Order(platform_order_id=testing_constants.MAGENTO_ORDER_1_PLATFORM_ORDER_ID,
                       status=Constants.ORDER_STATUS_PURCHASED,
                       purchase_timestamp=testing_constants.MAGENTO_ORDER_1_CREATED,
                       user_legacy=order1_user_legacy)
        order1.products.append(product0)
        order1.products.append(product1)

        order2_user_legacy = UserLegacy(email=testing_constants.MAGENTO_ORDER_2_EMAIL,
                                        name=testing_constants.MAGENTO_ORDER_2_NAME)
        order2 = Order(platform_order_id=testing_constants.MAGENTO_ORDER_2_PLATFORM_ORDER_ID,
                       status=Constants.ORDER_STATUS_PURCHASED,
                       purchase_timestamp=testing_constants.MAGENTO_ORDER_2_CREATED,
                       user_legacy=order2_user_legacy)

        shop.products.append(product0)
        shop.products.append(product1)
        shop.products.append(product2)
        shop.orders.append(order0)
        shop.orders.append(order1)
        shop.orders.append(order2)
        db.session.add(shop)
        db.session.commit()

        # test
        api = magento_api.API()
        current_orders = Order.query.filter_by(shop_id=shop.id).all()
        new_and_updated = api.fetch_new_and_updated_orders(current_orders, shop)
        self.assertEquals(len(new_and_updated), 1)
        db.session.add_all(new_and_updated)
        db.session.commit()

        self.assertEquals(len(self.outbox), 1)
        self.assertEquals(len(self.outbox[0].send_to), 1)
        self.assertEquals(self.outbox[0].send_to.pop(), testing_constants.MAGENTO_ORDER_1_EMAIL)
        self.assertEquals(self.outbox[0].subject,
                          Constants.DEFAULT_REVIEW_SUBJECT % (testing_constants.MAGENTO_ORDER_1_NAME.split()[0],
                                                              testing_constants.MAGENTO_SHOP_NAME))
        self.assertTrue(testing_constants.MAGENTO_ORDER_1_NAME.split()[0] in self.outbox[0].body)
        self.assertTrue(testing_constants.MAGENTO_PRODUCT_0_NAME in self.outbox[0].body)
        self.assertTrue(testing_constants.MAGENTO_PRODUCT_1_NAME in self.outbox[0].body)
        self.assertTrue(testing_constants.MAGENTO_SHOP_NAME in self.outbox[0].body)

        self.assertEquals(new_and_updated[0].platform_order_id, testing_constants.MAGENTO_ORDER_1_PLATFORM_ORDER_ID)
        self.assertEquals(new_and_updated[0].status, Constants.ORDER_STATUS_NOTIFIED)
        self.assertEquals(new_and_updated[0].purchase_timestamp,
                          datetime.datetime.strptime(testing_constants.MAGENTO_ORDER_1_CREATED, '%Y-%m-%d %H:%M:%S'))
        self.assertEquals(new_and_updated[0].shipment_timestamp,
                          datetime.datetime.strptime(testing_constants.MAGENTO_ORDER_1_SHIPPED, '%Y-%m-%d %H:%M:%S'))
        self.assertEquals(len(new_and_updated[0].products), 2)
        self.assertIsNotNone(new_and_updated[0].products[0])
        self.assertEquals(new_and_updated[0].products[0].platform_product_id,
                          testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID)
        self.assertIsNotNone(new_and_updated[0].products[1])
        self.assertEquals(new_and_updated[0].products[1].platform_product_id,
                          testing_constants.MAGENTO_PRODUCT_1_PLATFORM_PRODUCT_ID)
        self.assertEquals(len(new_and_updated[0].tasks), 2)
        self.assertEquals(new_and_updated[0].tasks[0].method, 'notify_for_review')
        self.assertEquals(str(new_and_updated[0].tasks[0].eta), '2015-12-19 12:00:00')
        self.assertEquals(new_and_updated[0].tasks[1].method, 'send_email')
        self.assertEquals(str(new_and_updated[0].tasks[1].eta), '2015-12-19 12:00:00')
        self.assertIsNotNone(new_and_updated[0].user_legacy)
        self.assertEquals(new_and_updated[0].user_legacy.email, testing_constants.MAGENTO_ORDER_1_EMAIL)
        self.assertEquals(new_and_updated[0].user_legacy.name, testing_constants.MAGENTO_ORDER_1_NAME)

        # tear down
        user = User.query.filter_by(email=testing_constants.NEW_USER_EMAIL).first()
        customer = user.customer[0]
        shop = Shop.query.filter_by(name=testing_constants.MAGENTO_SHOP_NAME).first()
        orders = Order.query.all()

        for product in shop.products:
            db.session.delete(product)
        db.session.delete(user)
        db.session.delete(customer)
        db.session.delete(shop)
        db.session.delete(shop)
        for order in orders:
            for review_request in order.review_requests:
                db.session.delete(review_request)
            db.session.delete(order)
        db.session.commit()
