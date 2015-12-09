from config import Constants
import datetime
import pytz
from dateutil import parser as date_parser
import testing_constants
from tests.framework import TestModel, expect_mail
from webapp import db, models, mail
from freezegun import freeze_time


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
    def test_set_notifications(self):
        # setup an order
        # TODO: create tests for variable combination of these objects not being set
        order = models.Order.query.first()
        product = models.Product(name=testing_constants.NEW_PRODUCT_NAME)
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
        #self.assertTrue(testing_constants.NEW_SHOP_NAME in self.outbox[0].body)

        order = models.Order.query.first()

        expected_notification_ts = date_parser.parse(testing_constants.ORDER_SHIPPED_AT).astimezone(pytz.utc).replace(tzinfo=None) + \
                                   datetime.timedelta(days=Constants.DIFF_SHIPMENT_NOTIFY)

        self.assertEquals(order.status, Constants.ORDER_STATUS_NOTIFIED)
        self.assertEquals(order.to_notify_timestamp,expected_notification_ts)
        self.assertEquals(len(order.tasks), 2)
        for task in order.tasks:
            self.assertEquals(task.status, 'SUCCESS')
            self.assertEquals(task.eta, date_parser.parse('2015-12-16 18:56:26'))

    def tearDown(self):
        order = models.Order.query.first()
        db.session.delete(order)
        db.session.commit()
        super(TestOrder, self).tearDown()
