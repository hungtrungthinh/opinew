import datetime
import pytz
from dateutil import parser as date_parser
from flask import jsonify, request
from webapp import db, models, exceptions, csrf
from webapp.api import api
from webapp.common import get_post_payload, catch_exceptions, verify_webhook, build_created_response


@api.route('/platform/shopify/products/create', methods=['POST'])
@catch_exceptions
@verify_webhook
@csrf.exempt
def platform_shopify_create_product():
    """
    Currently this works with the Shopify API
    From Webhook - create product
    "topic": "products\/create"
    """
    payload = get_post_payload()

    shopify_shop_domain = request.headers.get('X-Shopify-Shop-Domain')
    shop = models.Shop.query.filter_by(domain=shopify_shop_domain).first()
    if not shop:
        raise exceptions.DbException('no such shop %s' % shopify_shop_domain)

    platform_product_id = str(payload.get('id', ''))
    product_title = payload.get('title')

    product = models.Product(name=product_title, shop=shop, platform_product_id=platform_product_id)
    db.session.add(product)
    db.session.commit()
    return build_created_response('client.get_product', product_id=product.id)


@api.route('/platform/shopify/products/update', methods=['POST'])
@catch_exceptions
@verify_webhook
@csrf.exempt
def platform_shopify_update_product():
    """
    Currently this works with the Shopify API
    From Webhook - update product
    "topic": "products\/update"
    """
    payload = get_post_payload()

    platform_product_id = str(payload.get('id', ''))
    product_title = payload.get('title')

    shopify_shop_domain = request.headers.get('X-Shopify-Shop-Domain')
    shop = models.Shop.query.filter_by(domain=shopify_shop_domain).first()
    if not shop:
        raise exceptions.DbException('no such shop %s' % shopify_shop_domain)

    product = models.Product.query.filter_by(platform_product_id=platform_product_id, shop_id=shop.id).first()
    if not product:
        raise exceptions.DbException('no such product %s in shop %s' % (platform_product_id, shop.id))
    product.name = product_title

    db.session.add(product)
    db.session.commit()
    return jsonify({}), 200


@api.route('/platform/shopify/products/delete', methods=['POST'])
@catch_exceptions
@verify_webhook
@csrf.exempt
def platform_shopify_delete_product():
    """
    Currently this works with the Shopify API
    From Webhook - update product
    "topic": "products\/delete"
    """
    payload = get_post_payload()

    platform_product_id = str(payload.get('id', ''))
    shopify_shop_domain = request.headers.get('X-Shopify-Shop-Domain')

    shop = models.Shop.query.filter_by(domain=shopify_shop_domain).first()
    if not shop:
        raise exceptions.DbException('no such shop %s' % shopify_shop_domain)

    product = models.Product.query.filter_by(platform_product_id=platform_product_id, shop_id=shop.id).first()
    if not product:
        raise exceptions.DbException('no such product %s in shop %s' % (platform_product_id, shop.id))

    db.session.delete(product)
    db.session.commit()
    return jsonify({}), 200

@api.route('/platform/shopify/orders/create', methods=['POST'])
@catch_exceptions
@verify_webhook
@csrf.exempt
def platform_shopify_create_order():
    payload = get_post_payload()

    shopify_shop_domain = request.headers.get('X-Shopify-Shop-Domain')
    shop = models.Shop.query.filter_by(domain=shopify_shop_domain).first()
    if not shop:
        raise exceptions.DbException('no such shop %s' % shopify_shop_domain)

    platform_order_id = str(payload.get('id', ''))
    try:
        created_at_dt = date_parser.parse(payload.get('created_at')).astimezone(pytz.utc).replace(tzinfo=None)
    except:
        created_at_dt = datetime.datetime.utcnow()
    order = models.Order(platform_order_id=platform_order_id, shop=shop, purchase_timestamp=created_at_dt)

    customer_email = payload.get('customer', {}).get('email')
    customer_name = "%s %s" % (payload.get('customer', {}).get('first_name', ''),  payload.get('customer', {}).get('last_name', ''))
    existing_user = models.User.get_by_email_no_exception(customer_email)
    if existing_user:
        order.user = existing_user
    else:
        user_legacy, _ = models.UserLegacy.get_or_create_by_email(customer_email, name=customer_name)
        order.user_legacy  = user_legacy

    line_items = payload.get('line_items', [])
    for line_item in line_items:
        platform_product_id = str(line_item.get('product_id'))
        product = models.Product.query.filter_by(platform_product_id=platform_product_id, shop_id=shop.id).first()
        if product:
            order.products.append(product)
        else:
            variant = models.ProductVariant.query.filter_by(platform_variant_id=str(line_item.get('variant_id'))).first()
            if not variant:
                continue
            order.products.append(variant.product)
        order.products.append(product)

    db.session.add(order)
    db.session.commit()
    return build_created_response('client.get_order', order_id=order.id)


@api.route('/platform/shopify/orders/fulfill', methods=['POST'])
@catch_exceptions
@verify_webhook
@csrf.exempt
def platform_shopify_fulfill_order():
    payload = get_post_payload()

    shopify_shop_domain = request.headers.get('X-Shopify-Shop-Domain')

    shop = models.Shop.query.filter_by(domain=shopify_shop_domain).first()
    if not shop:
        raise exceptions.DbException('no such shop %s' % shopify_shop_domain)

    platform_order_id = str(payload.get('order_id', ''))

    order = models.Order.query.filter_by(platform_order_id=platform_order_id, shop_id=shop.id).first()
    delivery_tracking_number = payload.get('tracking_number')
    if order:
        created_at = payload.get('created_at')
        st = date_parser.parse(created_at).astimezone(pytz.utc).replace(tzinfo=None)
        order.ship(delivery_tracking_number, shipment_timestamp=st)

        db.session.add(order)
        db.session.commit()
    return jsonify({}), 200
