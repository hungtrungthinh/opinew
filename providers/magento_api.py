import datetime
from webapp import create_app, models, db
from magento import MagentoAPI
from sqlalchemy import and_
import sensitive
from config import Constants


class API(object):
    order_statuses = {
        'processing': Constants.ORDER_STATUS_PURCHASED,
        'pending_payment': Constants.ORDER_STATUS_PURCHASED,
        'csv_pending_hosted_payment': Constants.ORDER_STATUS_PURCHASED,
        'csv_paid': Constants.ORDER_STATUS_PURCHASED,
        'complete': Constants.ORDER_STATUS_SHIPPED,
        'csv_failed_hosted_payment': Constants.ORDER_STATUS_FAILED,
    }

    def __init__(self, domain, username, password, port=80):
        self.magento = MagentoAPI(domain, port, username, password)

    def create_new_order(self, morder, shop_id):
        order = models.Order(
            platform_order_id=morder.get('order_id'),
            status=self.order_statuses.get(morder.get('status'), Constants.ORDER_STATUS_PURCHASED),
            purchase_timestamp=datetime.datetime.strptime(morder.get('created_at'), '%Y-%m-%d %H:%M:%S'),
            shop_id=shop_id
        )
        # create user or get one from our db
        customer_email = morder.get('customer_email')
        customer_name = morder.get('billing_name')
        existing_user = models.User.get_by_email_no_exception(customer_email)
        if existing_user:
            order.user = existing_user
        else:
            legacy_user, _ = models.UserLegacy.get_or_create_by_email(customer_email, name=customer_name)
            order.legacy_user  = legacy_user


        # get the products for this order
        mproducts = self.magento.cart_product.list(morder.get('order_id'))
        for mproduct in mproducts:
            product = models.Product.query.filter_by(platform_product_id=mproduct.get('sku')).first()
            if product:
                order.products.append(product)
        return order

    def create_new_orders(self, morders, last_order_id, shop_id):
        orders = []
        for morder in morders:
            # check if this morder is newer than the latest we have in our db
            if int(morder.get('order_id', 0)) <= last_order_id:
                continue
            order = self.create_new_order(morder, shop_id)
            orders.append(order)
        return orders

    def get_shipments_info(self, current_orders):
        rv_mshipments = {}
        mshipments = self.magento.sales_order_shipment.list()
        for mshipment in mshipments:
            mshipment_details = self.magento.sales_order_shipment.info(mshipment.get('increment_id'))
            mshipment_order_id = int(mshipment_details.get('order_id', 0))
            if mshipment_order_id in [co.platform_order_id for co in current_orders]:
                rv_mshipments[mshipment_order_id] = mshipment_details
        return rv_mshipments

    def check_stalled_order(self, order):
        # check for stalled order
        purchase_dt = order.purchase_timestamp
        now = datetime.datetime.utcnow()
        diff = now - purchase_dt
        if diff.days >= Constants.DIFF_PURCHASE_STALL:
            order.status = Constants.ORDER_STATUS_STALLED
        return order

    def update_order_status(self, order):
        now = datetime.datetime.utcnow()
        shipment_dt = order.shipment_timestamp or now

        diff = now - shipment_dt

        # Delivery timestamp = shipment + 5
        delivery_dt = shipment_dt + datetime.timedelta(days=Constants.DIFF_SHIPMENT_DELIVERY)
        if not order.to_deliver_timestamp:
            order.to_deliver_timestamp = delivery_dt

            # Notify timestamp = delivery + 3
            if not order.to_notify_timestamp:
                notify_dt = delivery_dt + datetime.timedelta(days=Constants.DIFF_DELIVERY_NOTIFY)
                order.to_notify_timestamp = notify_dt

        # disambiguate what is the current status
        if diff.days >= Constants.DIFF_SHIPMENT_DELIVERY:
            # there has been more than 5 days since dispatch, should be at least delivered
            order.status = Constants.ORDER_STATUS_DELIVERED
            order.delivery_timestamp = delivery_dt
            if diff.days >= (Constants.DIFF_SHIPMENT_DELIVERY + Constants.DIFF_DELIVERY_NOTIFY):
                # there has been more than 3 days since delivery, notify for review...
                order.legacy()
        return order

    def update_order(self, morder, order, mshipment):
        order.status = self.order_statuses.get(morder.get('status'), Constants.ORDER_STATUS_PURCHASED)
        if not mshipment:
            order = self.check_stalled_order(order)
        else:
            # shipment_timestamp
            mshipment_ts = mshipment.get('created_at')
            shipment_dt = datetime.datetime.strptime(mshipment_ts, '%Y-%m-%d %H:%M:%S')
            order.shipment_timestamp = shipment_dt
            order = self.update_order_status(order)
        return order

    def update_orders(self, morders, current_orders):
        updated_orders = []
        kv_morders = {}

        # get shipments info
        rv_mshipments = self.get_shipments_info(current_orders)

        # creaate kv for quicker access
        for morder in morders:
            kv_morders[int(morder.get('order_id'))] = morder

        # update each order
        for current_order in current_orders:
            order_id = current_order.platform_order_id
            morder = kv_morders.get(order_id, {})
            mshipment = rv_mshipments.get(order_id, {})
            updated_order = self.update_order(morder, current_order, mshipment)
            updated_orders.append(updated_order)
        return updated_orders


def init(shop):
    api = API(shop.domain, shop.access_user, shop.access_token)

    # Update orders that are already on their way....
    to_update_orders = models.Order.query.filter(and_(models.Order.shop_id == shop.id,
                                                      models.Order.status.in_([
                                                          Constants.ORDER_STATUS_SHIPPED,
                                                          Constants.ORDER_STATUS_DELIVERED
                                                      ]))).all()
    for order in to_update_orders:
        order = api.update_order_status(order)
        db.session.add(order)

    # Flush to db
    db.session.commit()

    # Query the sales endpoint
    morders = api.magento.sales_order.list()

    # Update orders that are waiting to be dispatched...
    current_orders = models.Order.query.filter_by(shop_id=shop.id, status=Constants.ORDER_STATUS_PURCHASED).all()
    updated_orders = api.update_orders(morders, current_orders)
    db.session.add_all(updated_orders)

    # Flush to db
    db.session.commit()

    # Create new orders
    last_order = models.Order.query.filter_by(shop_id=shop.id).order_by(models.Order.platform_order_id.desc()).first()
    new_orders = api.create_new_orders(morders, last_order.platform_order_id, shop.id)
    db.session.add_all(new_orders)

    # Flush to db
    db.session.commit()
