import os
import sensitive
import datetime
from magento import MagentoAPI
from webapp import create_app, models
from importers.csv_utf_support import CSVUnicodeWriter
from config import Constants

app = create_app('db_dev')
app.app_context().push()

magento = MagentoAPI("www.beautykitchen.co.uk", 80, "opinew", sensitive.ADMIN_PASSWORD)

order_statuses = {
    'processing': Constants.ORDER_STATUS_PURCHASED,
    'pending_payment': Constants.ORDER_STATUS_PURCHASED,
    'csv_pending_hosted_payment': Constants.ORDER_STATUS_PURCHASED,
    'csv_paid': Constants.ORDER_STATUS_PURCHASED,
    'complete': Constants.ORDER_STATUS_SHIPPED,
    'csv_failed_hosted_payment': Constants.ORDER_STATUS_FAILED,
}

morders = magento.sales_order.list()

orders = {}

for morder in morders:
    order_products = []
    try:
        mproducts = magento.cart_product.list(morder.get('order_id'))
    except:
        continue
    for product in mproducts:
        order_products.append(product.get('sku'))
    order = {
        'user_email': morder.get('customer_email'),
        'user_name': morder.get('billing_name'),
        'platform_order_id': morder.get('order_id'),
        'delivery_tracking_number': '',
        'status': order_statuses.get(morder.get('status'), Constants.ORDER_STATUS_PURCHASED),
        'purchase_timestamp': morder.get('created_at'),
        'shipment_timestamp': None,
        'delivery_timestamp': None,
        'to_notify_timestamp': None,
        'notification_timestamp': None,
        'products': order_products
    }
    orders[morder.get('order_id')] = order

mshipments = magento.sales_order_shipment.list()
now = datetime.datetime.utcnow()
for mshipment in mshipments:
    mshipment_details = magento.sales_order_shipment.info(mshipment.get('increment_id'))
    mshipment_order_id = mshipment_details.get('order_id')
    if mshipment_order_id in orders:
        order = orders[mshipment_order_id]
        mshipment_timestamp = mshipment_details.get('created_at')
        order['shipment_timestamp'] = mshipment_timestamp
        shipment_datetime = datetime.datetime.strptime(mshipment_timestamp, '%Y-%m-%d %H:%M:%S')
        diff = now - shipment_datetime
        order['delivery_timestamp'] = shipment_datetime + datetime.timedelta(days=Constants.DIFF_SHIPMENT_DELIVERY)
        order['to_notify_timestamp'] = order['delivery_timestamp'] + datetime.timedelta(
            days=Constants.DIFF_DELIVERY_NOTIFY)
        if diff.days >= Constants.DIFF_SHIPMENT_DELIVERY:
            order['status'] = Constants.ORDER_STATUS_DELIVERED
            if diff.days >= (Constants.DIFF_SHIPMENT_DELIVERY + Constants.DIFF_DELIVERY_NOTIFY):
                order['status'] = Constants.ORDER_STATUS_NOTIFIED
                order['notification_timestamp'] = order['delivery_timestamp'] + datetime.timedelta(
                    days=Constants.DIFF_DELIVERY_NOTIFY)


basedir = os.path.abspath(os.path.dirname(__file__))

USER_NEXT_ID = 22

order_file_path = os.path.join(basedir, 'test_files', 'Order.csv')
order_product_file_path = os.path.join(basedir, 'test_files', 'Order_Product.csv')
user_file_path = os.path.join(basedir, 'test_files', 'User.csv')
user_roles_path = os.path.join(basedir, 'test_files', 'User_Role.csv')

with open(order_file_path, 'w') as of, open(order_product_file_path, 'w') as opf, \
        open(user_file_path, 'w') as uf, open(user_roles_path, 'w') as urf:
    of_csv_writer = CSVUnicodeWriter(of, lineterminator='\n')
    opf_csv_writer = CSVUnicodeWriter(opf, lineterminator='\n')
    uf_csv_writer = CSVUnicodeWriter(uf, lineterminator='\n')
    urf_csv_writer = CSVUnicodeWriter(urf, lineterminator='\n')

    of_headers = [
        'id',
        'platform_order_id',
        'user_id',
        'shop_id',
        'delivery_tracking_number',
        'status',
        'purchase_timestamp',
        'shipment_timestamp',
        'delivery_timestamp',
        'to_notify_timestamp',
        'notification_timestamp'
    ]
    of_csv_writer.writerow(of_headers)

    opf_headers = ['id', 'products']
    opf_csv_writer.writerow(opf_headers)

    uf_headers = ['id',
                  'email',
                  'password',
                  'temp_password',
                  'name',
                  'image_url',
                  'is_shop_owner']
    uf_csv_writer.writerow(uf_headers)

    urf_headers = ['id', 'roles']
    urf_csv_writer.writerow(urf_headers)

    orders = [b[1] for b in sorted(orders.iteritems(), key=lambda kv: int(kv[0]))]

    for i, order in enumerate(orders):
        order_id = i + 1
        user, is_new = models.User.get_or_create_by_email(order.get('user_email'), name=order.get('user_name'))
        if is_new:
            u_row = [
                str(USER_NEXT_ID),
                str(user.email),
                str(user.password),
                str(user.temp_password),
                str(user.name),
                str(''),
                str(0)
            ]
            uf_csv_writer.writerow(u_row)
            urf_csv_writer.writerow([str(USER_NEXT_ID), str(2)])
            user.id = USER_NEXT_ID
            USER_NEXT_ID += 1

        o_row = [
            str(order_id),
            str(order.get('platform_order_id', '')),
            str(user.id),
            str(3),
            str(order.get('delivery_tracking_number', '')),
            str(order.get('status', '')),
            str(order.get('purchase_timestamp', '')),
            str(order.get('shipment_timestamp', '')),
            str(order.get('delivery_timestamp', '')),
            str(order.get('to_notify_timestamp', '')),
            str(order.get('notification_timestamp', '')),
        ]
        of_csv_writer.writerow(o_row)

        for pid in order.get('products'):
            product = models.Product.query.filter_by(platform_product_id=pid).first()
            if product:
                p_row = [
                    str(order_id),
                    str(product.id)
                ]
                opf_csv_writer.writerow(p_row)
