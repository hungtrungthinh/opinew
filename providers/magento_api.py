import datetime
from flask import current_app
from webapp import models, db
from magento import MagentoAPI
from config import Constants


class API(object):
    order_statuses = {
        Constants.MAGENTO_STATUS_PROCESSING: Constants.ORDER_STATUS_PURCHASED,
        Constants.MAGENTO_STATUS_PENDING_PAYMENT: Constants.ORDER_STATUS_PURCHASED,
        Constants.MAGENTO_STATUS_CSV_PENDING_HOSTED_PAYMENT: Constants.ORDER_STATUS_PURCHASED,
        Constants.MAGENTO_STATUS_CSV_PAID: Constants.ORDER_STATUS_PURCHASED,
        Constants.MAGENTO_STATUS_COMPLETE: Constants.ORDER_STATUS_SHIPPED,
        Constants.MAGENTO_STATUS_CSV_FAILED_HOSTED_PAYMENT: Constants.ORDER_STATUS_FAILED,
    }

    def __init__(self, domain=None, username=None, password=None, port=80):
        from tests.virtual_webapp.vmagento.fake_api import FakeMagentoAPI

        self.magento = FakeMagentoAPI() if current_app.config.get('TESTING') else MagentoAPI(domain, port, username,
                                                                                             password)

    def create_new_order(self, morder):
        """
        Create new order object from morder
        :param morder: magento order object
        :return:
        """
        platform_order_id = morder.get('order_id')
        mplatfrom_order_increment_id = morder.get('increment_id')
        morder_created_at = datetime.datetime.strptime(morder.get('created_at'), '%Y-%m-%d %H:%M:%S')
        morder_customer_email = morder.get('customer_email')
        morder_billing_name = morder.get('billing_name')
        morder_status = self.order_statuses.get(morder.get('status'), Constants.ORDER_STATUS_PURCHASED)

        order = models.Order(
            platform_order_id=platform_order_id,
            status=morder_status,
            purchase_timestamp=morder_created_at,
        )
        # create user or get one from our db
        existing_user = models.User.get_by_email_no_exception(morder_customer_email)
        if existing_user:
            order.user = existing_user
        else:
            user_legacy, _ = models.UserLegacy.get_or_create_by_email(morder_customer_email, name=morder_billing_name)
            order.user_legacy = user_legacy

        # get the products for this order
        mproducts = self.magento.sales_order.info(mplatfrom_order_increment_id).get('items', [])
        for mproduct in mproducts:
            product = models.Product.query.filter_by(platform_product_id=mproduct.get('sku')).first()
            if product and product not in order.products:
                order.products.append(product)
        return order

    def get_shipments_info(self, earliest_purchase_day):
        rv_mshipments = {}
        mshipments = self.magento.sales_order_shipment.list()
        for mshipment in mshipments:
            this_shipment_ts = datetime.datetime.strptime(mshipment.get('created_at'), '%Y-%m-%d %H:%M:%S')
            if this_shipment_ts > earliest_purchase_day:
                mshipment_details = self.magento.sales_order_shipment.info(mshipment.get('increment_id'))
                mshipment_order_id = mshipment_details.get('order_id', '')
                rv_mshipments[mshipment_order_id] = mshipment_details
        return rv_mshipments

    def update_order(self, morder, order, mshipment):
        if order and mshipment:
            order.status = self.order_statuses.get(morder.get('status'), Constants.ORDER_STATUS_PURCHASED)
            mshipment_ts = mshipment.get('created_at')
            shipment_dt = datetime.datetime.strptime(mshipment_ts, '%Y-%m-%d %H:%M:%S')
            order.ship(shipment_timestamp=shipment_dt)
            if not order.tasks:
                order.set_notifications()
        return order

    def fetch_new_and_updated_orders(self, current_shop_orders, shop):
        """
        Gets newer and updated orders
        :param current_shop_orders: list of current orders in the db
        :return: list of new and updated orders
        """
        # Query the sales endpoint
        morders = self.magento.sales_order.list()
        new_and_updated_orders = []
        current_purchased_shop_orders_dict = {o.platform_order_id: o for o in current_shop_orders if
                                              o.status == Constants.ORDER_STATUS_PURCHASED}
        order_by_purchase = sorted(current_purchased_shop_orders_dict.values(),
                                   key=lambda x: getattr(x, 'purchase_timestamp'))
        earliest_purchase_day = getattr(order_by_purchase[0], 'purchase_timestamp') if order_by_purchase else datetime.datetime(1970, 1, 1)
        shipment_info = self.get_shipments_info(earliest_purchase_day)

        current_shop_orders_dict = {o.platform_order_id: o for o in current_shop_orders}
        for morder in morders:
            mplatform_order_id = morder.get('order_id')
            if mplatform_order_id in current_purchased_shop_orders_dict and \
                            mplatform_order_id in shipment_info:  # update order possibly
                order = current_purchased_shop_orders_dict.get(mplatform_order_id)
            elif mplatform_order_id not in current_shop_orders_dict:  # new order
                order = self.create_new_order(morder)
                order.shop = shop
            else:
                order = None
            mshipment = shipment_info.get(mplatform_order_id)
            order = self.update_order(morder, order, mshipment)
            if order:
                new_and_updated_orders.append(order)
        return new_and_updated_orders

    def fetch_new_and_updated_products(self, current_shop_products):
        """
        Gets newer and updated products
        :param current_shop_products: list of current products in the db
        :return: list of new and updated products
        """
        mproducts = self.magento.catalog_product.list()
        new_and_updated_products = []
        current_shop_products_dict = {p.platform_product_id: p for p in current_shop_products}
        for mproduct in mproducts:
            mplatform_product_id = mproduct.get('sku', None)
            try:
                mproduct_details = self.magento.catalog_product.info(mplatform_product_id)
            except:
                continue
            mproduct_name = mproduct.get('name', None)
            mproduct_active = True if mproduct_details.get(
                'status') == Constants.MAGENTO_PRODUCT_STATUS_AVAILABLE else False
            mproduct_description = mproduct_details.get('short_description')
            mproduct_urlkey = mproduct_details.get('url_key')
            if mplatform_product_id in current_shop_products_dict:
                # update product possibly
                product = current_shop_products_dict.get(mplatform_product_id)
                if not mproduct_name == product.name or \
                        not mproduct_active == product.active or \
                        not mproduct_description == product.short_description:
                    product.name = mproduct_name
                    product.active = mproduct_active
                    product.short_description = mproduct_description
                    new_and_updated_products.append(product)
            else:  # new product
                new_product = models.Product()
                new_product.platform_product_id = mplatform_product_id
                new_product.name = mproduct_name
                new_product.active = mproduct_active
                new_product.short_description = mproduct_description
                new_and_updated_products.append(new_product)
                new_product.urlkey = mproduct_urlkey
        return new_and_updated_products


def merge_products(shop, current_shop_products, new_and_updated_products):
    """
    Merge existing with new products
    :param shop: the shop
    :param current_shop_products: array of current product instances
    :param new_and_updated_products:  array of new and updated instances
    :return:
    """
    for p in new_and_updated_products:
        if p not in current_shop_products:
            # new product
            p.shop = shop
            if hasattr(p, 'urlkey'):
                pu_1 = models.ProductUrl(product=p, url="%s/%s" % (shop.domain, p.urlkey))
                pu_2 = models.ProductUrl(product=p, url="%s/(.)*%s" % (shop.domain, p.urlkey), is_regex=True)
                db.session.add(pu_1)
                db.session.add(pu_2)
        db.session.add(p)
    db.session.commit()


def init(shop):
    api = API(shop.domain, shop.access_user, shop.access_token)

    # Update products
    current_shop_products = models.Product.query.filter_by(shop_id=shop.id).all()
    new_and_updated_products = api.fetch_new_and_updated_products(current_shop_products)

    # Merge products
    merge_products(shop, current_shop_products, new_and_updated_products)

    # Create new orders
    current_shop_orders = models.Order.query.filter_by(shop_id=shop.id).all()
    new_and_updated_orders = api.fetch_new_and_updated_orders(current_shop_orders, shop)

    # Merge orders
    for nu_order in new_and_updated_orders:
        db.session.add(nu_order)

    # Flush to db
    db.session.commit()
