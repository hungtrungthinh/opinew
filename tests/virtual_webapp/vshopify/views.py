from flask import jsonify

from tests.virtual_webapp.vshopify import vshopify
from tests import testing_constants
from webapp.common import get_post_payload

webhooks_container = []

@vshopify.route('/admin/orders.json')
def orders():
    return jsonify({'orders': [{
        'id': testing_constants.NEW_ORDER_PLATFORM_ID,
        'fulfillment_status': None,
        'created_at': '2015-11-28T14:45:50+00:00',
        'cancelled_at': None,
        'browser_ip': testing_constants.NEW_ORDER_BROWSER_IP,
        'line_items': [{
            'id': testing_constants.NEW_PRODUCT_PLATFORM_ID,
            'product_id': testing_constants.NEW_PRODUCT_PLATFORM_ID,
            'variant_id': testing_constants.NEW_PRODUCT_PLATFORM_ID
        }],
        'customer': {
            'first_name': '',
            'last_name': ''
        }
    }]})


@vshopify.route('/admin/products.json')
def products():
    return jsonify({'products': [{
        'id': testing_constants.NEW_PRODUCT_PLATFORM_ID,
        'title': testing_constants.NEW_PRODUCT_NAME
    }]})


@vshopify.route('/admin/shop.json')
def shop():
    return jsonify({'shop': {'email': testing_constants.NEW_USER_EMAIL,
                             'shop_owner': testing_constants.NEW_USER_NAME}})


@vshopify.route('/admin/webhooks.json', methods=['POST'])
def webhooks():
    global webhooks_container
    payload = get_post_payload()
    webhooks_container.append(payload)
    return jsonify({})

@vshopify.route('/admin/webhooks/count.json')
def webhooks_count():
    global webhooks_container
    return jsonify({'count': len(webhooks_container)})

@vshopify.route('/clean_webhooks')
def clean_webhooks():
    global webhooks_container
    webhooks_container = []
    return jsonify({})

@vshopify.route('/admin/oauth/access_token', methods=['POST'])
def access_token():
    return jsonify({'access_token': 'hello'})
