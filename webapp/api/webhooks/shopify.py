from flask import jsonify, request
from webapp import db, models, exceptions
from webapp.api import api
from webapp.common import get_post_payload, catch_exceptions, verify_webhook, build_created_response


@api.route('/platform/shopify/products/create', methods=['POST'])
@catch_exceptions
@verify_webhook
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

    platform_product_id = payload.get('id')
    product_title = payload.get('title')

    product = models.Product(name=product_title, shop=shop, platform_product_id=platform_product_id)
    db.session.add(product)
    db.session.commit()
    return build_created_response('client.get_product', product_id=product.id)


@api.route('/platform/shopify/products/update', methods=['POST'])
@verify_webhook
@catch_exceptions
def platform_shopify_update_product():
    """
    Currently this works with the Shopify API
    From Webhook - update product
    "topic": "products\/update"
    """
    payload = get_post_payload()

    platform_product_id = payload.get('id')
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
@verify_webhook
@catch_exceptions
def platform_shopify_delete_product():
    """
    Currently this works with the Shopify API
    From Webhook - update product
    "topic": "products\/delete"
    """
    payload = get_post_payload()

    platform_product_id = payload.get('id')
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
@verify_webhook
@catch_exceptions
def platform_shopify_create_order():
    payload = get_post_payload()

    shopify_shop_domain = request.headers.get('X-Shopify-Shop-Domain')
    shop = models.Shop.query.filter_by(domain=shopify_shop_domain).first()
    if not shop:
        raise exceptions.DbException('no such shop %s' % shopify_shop_domain)

    customer_email = payload.get('customer', {}).get('email')
    opinew_user, _ = models.User.get_or_create_by_email(customer_email)

    platform_order_id = payload.get('id')

    order = models.Order(platform_order_id=platform_order_id, user=opinew_user, shop=shop)

    line_items = payload.get('line_items', [])
    for line_item in line_items:
        platform_product_id = line_item.get('product_id')
        product = models.Product.query.filter_by(platform_product_id=platform_product_id, shop_id=shop.id).first()
        order.products.append(product)

    db.session.add(order)
    db.session.commit()
    return build_created_response('client.get_order', order_id=order.id)


@api.route('/platform/shopify/orders/fulfill', methods=['POST'])
@verify_webhook
@catch_exceptions
def platform_shopify_fulfill_order():
    payload = get_post_payload()

    shopify_shop_domain = request.headers.get('X-Shopify-Shop-Domain')

    shop = models.Shop.query.filter_by(domain=shopify_shop_domain).first()
    if not shop:
        raise exceptions.DbException('no such shop %s' % shopify_shop_domain)

    platform_order_id = payload.get('order_id')

    order = models.Order.query.filter_by(platform_order_id=platform_order_id, shop_id=shop.id).first()
    delivery_tracking_number = payload.get('tracking_number')
    if order:
        order.ship(delivery_tracking_number)

        db.session.add(order)
        db.session.commit()
    return jsonify({}), 200
