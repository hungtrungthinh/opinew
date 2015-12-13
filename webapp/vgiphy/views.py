from flask import jsonify
from webapp.vgiphy import vgiphy


@vgiphy.route('/search')
def search():
    return jsonify({})


@vgiphy.route('/trending')
def trending():
    return jsonify({})
