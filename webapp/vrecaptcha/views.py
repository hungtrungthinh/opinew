from flask import jsonify
from webapp.vrecaptcha import vrecaptcha


@vrecaptcha.route('/recaptcha/api/siteverify', methods=['POST'])
def siteverify():
    return jsonify({
        'success': True
    })
