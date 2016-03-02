from flask import jsonify

from tests.virtual_webapp.vstripe import vstripe


@vstripe.route('/v1/customers', methods=['POST'])
def create_customer():
    return jsonify({
        "id": "cus_7SdLLs7HKKgWdK",
        "object": "customer",
        "account_balance": 0,
        "created": 1449091448,
        "currency": "gbp",
        "default_source": None,
        "delinquent": False,
        "description": "lc.carrier@hotmail.com",
        "discount": None,
        "email": None,
        "livemode": False,
        "metadata": {
        },
        "shipping": None,
        "sources": {
            "object": "list",
            "data": [
                {}
            ],
            "has_more": False,
            "total_count": 0,
            "url": "/v1/customers/cus_7SdLLs7HKKgWdK/sources"
        },
        "subscriptions": {
            "object": "list",
            "data": [
                {}
            ],
            "has_more": False,
            "total_count": 0,
            "url": "/v1/customers/cus_7SdLLs7HKKgWdK/subscriptions"
        }
    })


@vstripe.route('/v1/customers/<customer_id>', methods=['POST'])
def update_customer(customer_id):
    return jsonify({
        "id": "cus_7SdLLs7HKKgWdK",
        "object": "customer",
        "account_balance": 0,
        "created": 1449091448,
        "currency": "gbp",
        "default_source": None,
        "delinquent": False,
        "description": "Customer for test@example.com",
        "discount": None,
        "email": None,
        "livemode": False,
        "metadata": {
        },
        "shipping": None,
        "sources": {
            "object": "list",
            "data": [
                {}
            ],
            "has_more": False,
            "total_count": 0,
            "url": "/v1/customers/cus_7SdLLs7HKKgWdK/sources"
        },
        "subscriptions": {
            "object": "list",
            "data": [
                {
                     "id": "sub_7UjOQrtOFQMFQL",
                }
            ],
            "has_more": False,
            "total_count": 0,
            "url": "/v1/customers/cus_7SdLLs7HKKgWdK/subscriptions"
        }
    })


@vstripe.route('/v1/customers/<customer_id>', methods=['GET'])
def get_customer(customer_id):
    return jsonify({
        "id": "cus_7SdLLs7HKKgWdK",
        "object": "customer",
        "account_balance": 0,
        "created": 1449091448,
        "currency": "gbp",
        "default_source": None,
        "delinquent": False,
        "description": "lc.carrier@hotmail.com",
        "discount": None,
        "email": None,
        "livemode": False,
        "metadata": {
        },
        "shipping": None,
        "sources": {
            "object": "list",
            "data": [
                {}
            ],
            "has_more": False,
            "total_count": 0,
            "url": "/v1/customers/cus_7SdLLs7HKKgWdK/sources"
        },
        "subscriptions": {
            "object": "list",
            "data": [
                {}
            ],
            "has_more": False,
            "total_count": 0,
            "url": "/v1/customers/cus_7SdLLs7HKKgWdK/subscriptions"
        }
    })


@vstripe.route('/v1/subscriptions', methods=['POST'])
def create_subscription():
    return jsonify({
        "id": "sub_7UjOQrtOFQMFQL",
        "object": "subscription",
        "application_fee_percent": None,
        "cancel_at_period_end": False,
        "canceled_at": None,
        "current_period_end": 1452253627,
        "current_period_start": 1449575227,
        "customer": "cus_7SdLLs7HKKgWdK",
        "discount": None,
        "ended_at": None,
        "metadata": {
        },
        "plan": {
            "id": "Free",
            "object": "plan",
            "amount": 0,
            "created": 1445348186,
            "currency": "gbp",
            "interval": "month",
            "interval_count": 1,
            "livemode": False,
            "metadata": {
            },
            "name": "Free",
            "statement_descriptor": None,
            "trial_period_days": None
        },
        "quantity": 1,
        "start": 1449575227,
        "status": "active",
        "tax_percent": None,
        "trial_end": None,
        "trial_start": None
    })


@vstripe.route('/v1/customers/<subscription_id>/subscriptions', methods=['POST'])
def create_customer_subscription(subscription_id):
    return jsonify({
        "id": "sub_7UjOQrtOFQMFQL",
        "object": "subscription",
        "application_fee_percent": None,
        "cancel_at_period_end": False,
        "canceled_at": None,
        "current_period_end": 1452253627,
        "current_period_start": 1449575227,
        "customer": "cus_7SdLLs7HKKgWdK",
        "discount": None,
        "ended_at": None,
        "metadata": {
        },
        "plan": {
            "id": "Free",
            "object": "plan",
            "amount": 0,
            "created": 1445348186,
            "currency": "gbp",
            "interval": "month",
            "interval_count": 1,
            "livemode": False,
            "metadata": {
            },
            "name": "Free",
            "statement_descriptor": None,
            "trial_period_days": None
        },
        "quantity": 1,
        "start": 1449575227,
        "status": "active",
        "tax_percent": None,
        "trial_end": None,
        "trial_start": None
    })


@vstripe.route('/v1/customers/<customer_id>/subscriptions/<subscription_id>', methods=['GET', 'DELETE'])
def get_customer_subscription(customer_id, subscription_id):
    return jsonify({
        "id": "sub_7UjOQrtOFQMFQL",
        "object": "subscription",
        "application_fee_percent": None,
        "cancel_at_period_end": False,
        "canceled_at": None,
        "current_period_end": 1452253627,
        "current_period_start": 1449575227,
        "customer": "cus_7SdLLs7HKKgWdK",
        "discount": None,
        "ended_at": None,
        "metadata": {
        },
        "plan": {
            "id": "Free",
            "object": "plan",
            "amount": 0,
            "created": 1445348186,
            "currency": "gbp",
            "interval": "month",
            "interval_count": 1,
            "livemode": False,
            "metadata": {
            },
            "name": "Free",
            "statement_descriptor": None,
            "trial_period_days": None
        },
        "quantity": 1,
        "start": 1449575227,
        "status": "active",
        "tax_percent": None,
        "trial_end": None,
        "trial_start": None
    })