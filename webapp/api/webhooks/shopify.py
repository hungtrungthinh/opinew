from flask import jsonify, request, g
from webapp import db, models, exceptions, csrf
from webapp.api import api
from webapp.common import get_post_payload, catch_exceptions, verify_webhook, build_created_response
from providers.shopify_api import OpinewShopifyFacade


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
    existing_product = models.Product.query.filter_by(platform_product_id=platform_product_id).first()
    if existing_product:
        raise exceptions.DbException('Product already exists', status_code=401)
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
    opinew_shopify = OpinewShopifyFacade(shop=shop)
    opinew_shopify.create_order(payload)
    return jsonify({}), 201


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
    opinew_shopify = OpinewShopifyFacade(shop=shop)
    opinew_shopify.fulfill_order(payload)
    return jsonify({}), 200


@api.route('/platform/shopify/app/uninstalled', methods=['POST'])
@catch_exceptions
@verify_webhook
@csrf.exempt
def platform_shopify_app_uninstalled():
    shopify_shop_domain = request.headers.get('X-Shopify-Shop-Domain')

    shop = models.Shop.query.filter_by(domain=shopify_shop_domain).first()
    if not shop:
        raise exceptions.DbException('no such shop %s' % shopify_shop_domain)

    # revoke tasks
    for order in shop.orders:
        for task in order.tasks:
            task.revoke()
            db.session.add(task)
    # Mark shop as inactive
    shop.active = False
    db.session.add(shop)

    # Find subscription
    subscription = shop.owner.customer[0].subscription[0]

    #Update trialed for days
    g.db.Subscription.cancel(subscription)
    g.db.add(subscription)
    g.db.push()
    return jsonify({}), 200
