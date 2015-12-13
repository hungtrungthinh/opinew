from flask import jsonify

from tests.virtual_webapp.vgiphy import vgiphy


@vgiphy.route('/search')
def search():
    return jsonify({})


@vgiphy.route('/trending')
def trending():
    return jsonify({})
