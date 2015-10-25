from flask import jsonify, request
from webapp import db, models
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
    shop = models.Shop.get_by_shop_domain(shopify_shop_domain)

    platform_product_id = payload.get('id')
    product_title = payload.get('title')

    product = models.Product(name=product_title)

    shop_product = models.ShopProduct(product=product, shop=shop, platform_product_id=platform_product_id)
    db.session.add(shop_product)
    db.session.commit()
    return build_created_response('.get_product', product_id=product.id)


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

    shop_product = models.ShopProduct.get_by_platform_product_id(platform_product_id)
    product = shop_product.product
    product.label = product_title

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

    shop_product = models.ShopProduct.get_by_platform_product_id(platform_product_id)
    db.session.delete(shop_product)
    db.session.commit()
    return jsonify({}), 200


@api.route('/platform/shopify/orders/create', methods=['POST'])
@verify_webhook
@catch_exceptions
def platform_shopify_create_order():
    payload = get_post_payload()

    shop_domain = request.headers.get('X-Shopify-Shop-Domain')
    shop = models.Shop.get_by_shop_domain(shop_domain)

    customer_email = payload.get('customer', {}).get('email')
    customer = models.User.get_or_create_by_email(customer_email)

    platform_order_id = payload.get('id')

    order = models.Order(platform_order_id=platform_order_id, user=customer, shop=shop)

    line_items = payload.get('line_items', [])
    for line_item in line_items:
        platform_product_id = line_item.get('product_id')
        shop_product = models.ShopProduct.get_by_platform_product_id(platform_product_id)
        product = shop_product.product
        order.products.append(product)

    db.session.add(order)
    db.session.commit()
    return build_created_response('.get_order', order_id=order.id)


@api.route('/platform/shopify/orders/fulfill', methods=['POST'])
@verify_webhook
@catch_exceptions
def platform_shopify_fulfill_order():
    payload = get_post_payload()
    platform_order_id = payload.get('order_id')

    order = models.Order.get_by_platform_order_id(platform_order_id)
    delivery_tracking_number = payload.get('tracking_number')
    order.ship(delivery_tracking_number)

    db.session.add(order)
    db.session.commit()
    return jsonify({}), 200
