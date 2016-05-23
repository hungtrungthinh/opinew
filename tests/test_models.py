from config import Constants
import datetime
import pytz
from dateutil import parser as date_parser
import testing_constants
from tests.framework import TestModel, expect_mail
from webapp import db, models, mail
from freezegun import freeze_time
from webapp.exceptions import DbException


class TestOrder(TestModel):
    def setUp(self):
        super(TestOrder, self).setUp()
        order = models.Order()
        db.session.add(order)
        db.session.commit()

    @freeze_time(testing_constants.ORDER_NOW)
    def test_ship_order(self):
        order = models.Order.query.first()
        order.ship(shipment_timestamp=testing_constants.ORDER_SHIPPED_AT)
        order = models.Order.query.first()
        expected_shipment_ts = date_parser.parse(testing_constants.ORDER_SHIPPED_AT).astimezone(pytz.utc).replace(tzinfo=None)
        self.assertEquals(order.status, Constants.ORDER_STATUS_SHIPPED)
        self.assertEquals(order.shipment_timestamp, expected_shipment_ts)

    @expect_mail
    @freeze_time(testing_constants.ORDER_NOW)
    def test_set_email_notifications(self):
        # setup an order
        order = models.Order.query.first()
        product = models.Product(name=testing_constants.NEW_PRODUCT_NAME, platform_product_id=testing_constants.NEW_PRODUCT_PLATFORM_ID)
        user_buyer = models.User(email=testing_constants.NEW_USER_EMAIL, name=testing_constants.NEW_USER_NAME)
        order.user = user_buyer
        user_shop_owner = models.User()
        models.Customer(user=user_shop_owner)
        shop = models.Shop(name=testing_constants.NEW_SHOP_NAME)
        shop.owner = user_shop_owner
        product.shop = shop
        order.shop = shop
        order.products.append(product)
        order.shipment_timestamp = date_parser.parse(testing_constants.ORDER_SHIPPED_AT).astimezone(pytz.utc).replace(tzinfo=None)

        # The results from the asynchronous tasks are executed immediately
        order.set_notifications()
        self.assertEquals(len(self.outbox), 1)
        self.assertEquals(len(self.outbox[0].send_to), 1)
        self.assertEquals(self.outbox[0].send_to.pop(), testing_constants.NEW_USER_EMAIL)
        self.assertEquals(self.outbox[0].subject, Constants.DEFAULT_REVIEW_SUBJECT %(testing_constants.NEW_USER_NAME.split()[0],
                          testing_constants.NEW_SHOP_NAME))
        self.assertTrue(testing_constants.NEW_USER_NAME.split()[0] in self.outbox[0].body)
        self.assertTrue(testing_constants.NEW_PRODUCT_NAME in self.outbox[0].body)
        self.assertTrue(testing_constants.NEW_SHOP_NAME in self.outbox[0].body)

        order = models.Order.query.first()

        expected_notification_ts = date_parser.parse(testing_constants.ORDER_SHIPPED_AT).astimezone(pytz.utc).replace(tzinfo=None) + \
                                   datetime.timedelta(days=Constants.DIFF_SHIPMENT_NOTIFY)

        self.assertEquals(order.status, Constants.ORDER_STATUS_NOTIFIED)
        self.assertEquals(order.to_notify_timestamp,expected_notification_ts)
        self.assertEquals(len(order.tasks), 2)
        for task in order.tasks:
            self.assertEquals(task.status, 'SUCCESS')
            self.assertEquals(task.eta, date_parser.parse('2015-12-16 18:56:26'))

    @freeze_time(testing_constants.ORDER_NOW)
    def test_set_email_notifications_no_buyer(self):
        order = models.Order.query.first()
        product = models.Product(name=testing_constants.NEW_PRODUCT_NAME, platform_product_id=testing_constants.NEW_PRODUCT_PLATFORM_ID)
        user_buyer = None
        order.user = user_buyer
        user_shop_owner = models.User()
        models.Customer(user=user_shop_owner)
        shop = models.Shop(name=testing_constants.NEW_SHOP_NAME)
        shop.owner = user_shop_owner
        product.shop = shop
        order.shop = shop
        order.products.append(product)
        order.shipment_timestamp = date_parser.parse(testing_constants.ORDER_SHIPPED_AT).astimezone(pytz.utc).replace(tzinfo=None)

        # The results from the asynchronous tasks are executed immediately
        with self.assertRaises(DbException):
            order.set_notifications()

    @freeze_time(testing_constants.ORDER_NOW)
    def test_set_email_notifications_no_shop(self):
        order = models.Order.query.first()
        product = models.Product(name=testing_constants.NEW_PRODUCT_NAME, platform_product_id=testing_constants.NEW_PRODUCT_PLATFORM_ID)
        user_buyer = models.User(email=testing_constants.NEW_USER_EMAIL, name=testing_constants.NEW_USER_NAME)
        order.user = user_buyer
        user_shop_owner = models.User()
        models.Customer(user=user_shop_owner)
        shop = None
        product.shop = shop
        order.shop = shop
        order.products.append(product)
        order.shipment_timestamp = date_parser.parse(testing_constants.ORDER_SHIPPED_AT).astimezone(pytz.utc).replace(tzinfo=None)

        # The results from the asynchronous tasks are executed immediately
        with self.assertRaises(DbException):
            order.set_notifications()

    @freeze_time(testing_constants.ORDER_NOW)
    def test_set_email_notifications_no_products_in_order(self):
        order = models.Order.query.first()
        user_buyer = models.User(email=testing_constants.NEW_USER_EMAIL, name=testing_constants.NEW_USER_NAME)
        order.user = user_buyer
        user_shop_owner = models.User()
        models.Customer(user=user_shop_owner)
        shop = models.Shop(name=testing_constants.NEW_SHOP_NAME)
        shop.owner = user_shop_owner
        order.shop = shop
        order.shipment_timestamp = date_parser.parse(testing_constants.ORDER_SHIPPED_AT).astimezone(pytz.utc).replace(tzinfo=None)

        # The results from the asynchronous tasks are executed immediately
        with self.assertRaises(DbException):
            order.set_notifications()

    @freeze_time(testing_constants.ORDER_NOW)
    def test_set_email_notifications_no_shipment_timestamp(self):
        order = models.Order.query.first()
        product = models.Product(name=testing_constants.NEW_PRODUCT_NAME, platform_product_id=testing_constants.NEW_PRODUCT_PLATFORM_ID)
        user_buyer = models.User(email=testing_constants.NEW_USER_EMAIL, name=testing_constants.NEW_USER_NAME)
        order.user = user_buyer
        user_shop_owner = models.User()
        models.Customer(user=user_shop_owner)
        shop = models.Shop(name=testing_constants.NEW_SHOP_NAME)
        shop.owner = user_shop_owner
        product.shop = shop
        order.shop = shop
        order.products.append(product)
        order.shipment_timestamp = None
        # The results from the asynchronous tasks are executed immediately
        with self.assertRaises(DbException):
            order.set_notifications()

    @expect_mail
    @freeze_time(testing_constants.ORDER_NOW)
    def test_set_email_notifications_legacy_user(self):
        order = models.Order.query.first()
        product = models.Product(name=testing_constants.NEW_PRODUCT_NAME, platform_product_id=testing_constants.NEW_PRODUCT_PLATFORM_ID)
        user_buyer = models.UserLegacy(email=testing_constants.NEW_USER_EMAIL, name=testing_constants.NEW_USER_NAME)
        order.user_legacy = user_buyer
        user_shop_owner = models.User()
        models.Customer(user=user_shop_owner)
        shop = models.Shop(name=testing_constants.NEW_SHOP_NAME)
        shop.owner = user_shop_owner
        product.shop = shop
        order.shop = shop
        order.products.append(product)
        order.shipment_timestamp = date_parser.parse(testing_constants.ORDER_SHIPPED_AT).astimezone(pytz.utc).replace(tzinfo=None)

        # The results from the asynchronous tasks are executed immediately
        order.set_notifications()
        self.assertEquals(len(self.outbox), 1)
        self.assertEquals(len(self.outbox[0].send_to), 1)
        self.assertEquals(self.outbox[0].send_to.pop(), testing_constants.NEW_USER_EMAIL)
        self.assertEquals(self.outbox[0].subject, Constants.DEFAULT_REVIEW_SUBJECT %(testing_constants.NEW_USER_NAME.split()[0],
                          testing_constants.NEW_SHOP_NAME))
        self.assertTrue(testing_constants.NEW_USER_NAME.split()[0] in self.outbox[0].body)
        self.assertTrue(testing_constants.NEW_PRODUCT_NAME in self.outbox[0].body)
        self.assertTrue(testing_constants.NEW_SHOP_NAME in self.outbox[0].body)

        order = models.Order.query.first()

        expected_notification_ts = date_parser.parse(testing_constants.ORDER_SHIPPED_AT).astimezone(pytz.utc).replace(tzinfo=None) + \
                                   datetime.timedelta(days=Constants.DIFF_SHIPMENT_NOTIFY)

        self.assertEquals(order.status, Constants.ORDER_STATUS_NOTIFIED)
        self.assertEquals(order.to_notify_timestamp,expected_notification_ts)
        self.assertEquals(len(order.tasks), 2)
        for task in order.tasks:
            self.assertEquals(task.status, 'SUCCESS')
            self.assertEquals(task.eta, date_parser.parse('2015-12-16 18:56:26'))

    @freeze_time(testing_constants.ORDER_NOW)
    def test_get_order_by_id(self):
        order = models.Order.query.first()
        product = models.Product(name=testing_constants.NEW_PRODUCT_NAME, platform_product_id=testing_constants.NEW_PRODUCT_PLATFORM_ID)
        user_buyer = models.User(email=testing_constants.NEW_USER_EMAIL, name=testing_constants.NEW_USER_NAME)
        order.user = user_buyer
        user_shop_owner = models.User()
        models.Customer(user=user_shop_owner)
        shop = models.Shop(name=testing_constants.NEW_SHOP_NAME)
        shop.owner = user_shop_owner
        product.shop = shop
        order.shop = shop
        order.products.append(product)
        order.shipment_timestamp = date_parser.parse(testing_constants.ORDER_SHIPPED_AT).astimezone(pytz.utc).replace(tzinfo=None)
        order_id = order.id
        db.session.add(order)
        db.session.commit()

        retrieved_order = models.Order.get_by_id(order_id=order_id)
        self.assertTrue(retrieved_order is not None)
        self.assertTrue(isinstance(retrieved_order, models.Order))

    ################################

    def test_get_user_by_email(self):
        user_buyer = models.User(email=testing_constants.NEW_USER_EMAIL, name=testing_constants.NEW_USER_NAME)
        db.session.add(user_buyer)
        db.session.commit()
        user = models.User.get_by_email(email=testing_constants.NEW_USER_EMAIL)

        self.assertEquals(user_buyer.email, user.email)
        self.assertEquals(user_buyer.id, user.id)
        self.assertEquals(user_buyer.name, user.name)
        db.session.delete(user)
        db.session.commit()

    def test_create_review_request(self):
        user_buyer = models.User(email=testing_constants.NEW_USER_EMAIL, name=testing_constants.NEW_USER_NAME)
        user_shop_owner = models.User(is_shop_owner=True)
        order = models.Order()
        product = models.Product(name=testing_constants.NEW_PRODUCT_NAME, platform_product_id=testing_constants.NEW_PRODUCT_PLATFORM_ID)
        order.user = user_buyer
        customer = models.Customer(user=user_shop_owner)
        shop = models.Shop(name=testing_constants.NEW_SHOP_NAME)
        shop.owner = user_shop_owner
        product.shop = shop
        order.shop = shop
        order.products.append(product)

        #creates a review request and returns a token associated with it
        review_request_token = models.ReviewRequest.create(to_user=user_buyer, from_customer=customer,
                                                           for_product=product, for_shop=shop, for_order=order)
        review_request = models.ReviewRequest.query.filter_by(token=review_request_token).first()

        self.assertEqual(review_request.token, review_request_token)
        self.assertEqual(review_request.for_shop.name, shop.name)
        self.assertEqual(review_request.from_customer.user.is_shop_owner, user_shop_owner.is_shop_owner)

    def test_create_review_request_repeated_products(self):
        order = models.Order.query.first()
        user_shop_owner = models.User()
        models.Customer(user=user_shop_owner)
        shop = models.Shop(name=testing_constants.NEW_SHOP_NAME)
        shop.owner = user_shop_owner
        order.shop = shop

        product1 = models.Product(platform_product_id=testing_constants.NEW_PRODUCT_PLATFORM_ID)
        product2 = models.Product(platform_product_id=testing_constants.NEW_PRODUCT_PLATFORM_ID_2)
        # add the first product twice
        order.products.append(product1)
        order.products.append(product1)  # not a typo!. << Good to know ;) -- T.
        order.products.append(product2)
        order.create_review_requests(order.id)
        self.assertEquals(len(order.review_requests), 2)

    def tearDown(self):
        order = models.Order.query.first()
        if order:
            db.session.delete(order)
            db.session.commit()
        self.refresh_db()
        super(TestOrder, self).tearDown()
