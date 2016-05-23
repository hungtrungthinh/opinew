from flask import jsonify

from tests.virtual_webapp.vrecaptcha import vrecaptcha
from webapp.common import get_post_payload
from tests import testing_constants
import sensitive


@vrecaptcha.route('/recaptcha/api/siteverify', methods=['POST'])
def siteverify():
    payload = get_post_payload()
    secret = payload.get('secret')
    g_recaptcha_response = payload.get('response')
    success = False
    if secret and g_recaptcha_response and \
                    g_recaptcha_response == testing_constants.RECAPTCHA_FAKE_PASS and \
                    secret == sensitive.RECAPTCHA_SECRET:
        success = True

    return jsonify({
        'success': success
    })
