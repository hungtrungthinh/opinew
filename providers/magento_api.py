import datetime
from webapp import models, db
from magento import MagentoAPI
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
        platform_order_id = morder.get('order_id')
        order = models.Order(
            platform_order_id=platform_order_id,
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
            user_legacy, _ = models.UserLegacy.get_or_create_by_email(customer_email, name=customer_name)
            order.user_legacy = user_legacy

        # get the products for this order
        mproducts = self.magento.sales_order.info(morder.get('increment_id')).get('items', [])
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

    def update_order(self, morder, order, mshipment):
        order.status = self.order_statuses.get(morder.get('status'), Constants.ORDER_STATUS_PURCHASED)
        if not mshipment:
            order = self.check_stalled_order(order)
        else:
            # shipment_timestamp
            mshipment_ts = mshipment.get('created_at')
            shipment_dt = datetime.datetime.strptime(mshipment_ts, '%Y-%m-%d %H:%M:%S')
            order.ship(shipment_timestamp=shipment_dt)
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

    def update_products(self, mproducts, current_shop_products):
        new_and_updated_products = []
        current_shop_products_dict = {p.platform_product_id: p for p in current_shop_products}
        for mproduct in mproducts:
            mplatform_product_id = mproduct.get('sku', None)
            try:
                mproduct_details = self.magento.catalog_product.info(mplatform_product_id)
            except:
                continue
            mproduct_name = mproduct.get('name', None)
            mproduct_active = True if mproduct_details['status'] == '1' else False
            mproduct_description = mproduct_details['short_description']
            mproduct_urlkey = mproduct_details['url_key']
            if mplatform_product_id not in current_shop_products_dict:
                new_product = models.Product(platform_product_id=mplatform_product_id)
                new_product.name = mproduct_name
                new_product.active = mproduct_active
                new_product.short_description = mproduct_description
                new_and_updated_products.append(new_product)
                new_product.urlkey = mproduct_urlkey
            else:
                product = current_shop_products_dict.get(mplatform_product_id)
                if not product:
                    continue
                if not mproduct_name == product.name or \
                    not mproduct_active == product.active or \
                    not mproduct_description == product.short_description:
                    product.name = mproduct_name
                    product.active = mproduct_active
                    product.short_description = mproduct_description
                    new_and_updated_products.append(product)
        return new_and_updated_products



def init(shop):
    api = API(shop.domain, shop.access_user, shop.access_token)

    # Update products
    current_shop_products = models.Product.query.filter_by(shop_id=shop.id).all()

    # Query the products endpoint
    mproducts = api.magento.catalog_product.list()

    # Merge
    updated_products = api.update_products(mproducts, current_shop_products)
    for p in updated_products:
        p.shop = shop
        if hasattr(p, 'urlkey'):
            pu_1 = models.ProductUrl(product=p, url="%s/%s" % (shop.domain, p.urlkey))
            pu_2 = models.ProductUrl(product=p, url="%s/(.)*%s" % (shop.domain, p.urlkey), is_regex=True)
            db.session.add(pu_1)
            db.session.add(pu_2)
        db.session.add(p)
    db.session.commit()

    # Query the sales endpoint
    morders = api.magento.sales_order.list()

    # Create new orders
    last_order = models.Order.query.filter_by(shop_id=shop.id).order_by(models.Order.platform_order_id.desc()).first()
    new_orders = api.create_new_orders(morders, last_order.platform_order_id if last_order else 0, shop.id)
    db.session.add_all(new_orders)

    # Flush to db
    db.session.commit()

    # Update orders that are waiting to be dispatched...
    purchased_orders = models.Order.query.filter_by(shop_id=shop.id, status=Constants.ORDER_STATUS_PURCHASED).all()
    shipped_orders = models.Order.query.filter_by(shop_id=shop.id, status=Constants.ORDER_STATUS_SHIPPED).all()
    current_orders = purchased_orders + shipped_orders
    updated_orders = api.update_orders(morders, current_orders)
    db.session.add_all(updated_orders)

    # Flush to db
    db.session.commit()
