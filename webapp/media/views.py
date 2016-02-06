from flask import send_from_directory, g, request, url_for, jsonify, abort
from flask_resize import resize
from webapp.media import media
from webapp import review_images, user_images


@media.route('/upload/user', methods=['POST'])
def upload_user_image():
    if 'image' in request.files:
        filename = user_images.save(request.files['image'])
        return jsonify(
            {'image_url': g.config.get('OPINEW_API_SERVER') + url_for('media.get_user_image', filename=filename)})
    return '', 400


@media.route('/user/', defaults={'filename': None})
@media.route('/user/<path:filename>')
def get_user_image(filename):
    if not filename:
        abort(404)
    return send_from_directory(g.config.get('UPLOADED_USERIMAGES_DEST'), filename)


@media.route('/upload/review', methods=['POST'])
def upload_review_image():
    if 'image' in request.files:
        filename = review_images.save(request.files['image'])
        return jsonify({'image_url': resize(g.config.get('OPINEW_API_SERVER') + url_for('media.get_review_image', filename=filename), '600x400')})
    return '', 400


@media.route('/review/', defaults={'filename': None})
@media.route('/review/<path:filename>')
def get_review_image(filename):
    if not filename:
        abort(404)
    return send_from_directory(g.config.get('UPLOADED_REVIEWIMAGES_DEST'), filename)


@media.route('/cache/', defaults={'filename': None})
@media.route('/cache/<path:filename>')
def get_cached_image(filename):
    if not filename:
        abort(404)
    return send_from_directory(g.config.get('RESIZE_CACHE'), filename)


@media.route('/upload/shop', methods=['POST'])
def upload_shop_image():
    if 'image' in request.files:
        filename = review_images.save(request.files['image'])
        return jsonify(
            {'image_url': g.config.get('OPINEW_API_SERVER') + url_for('media.get_shop_image', filename=filename)})
    return '', 400


@media.route('/shop/', defaults={'filename': None})
@media.route('/shop/<path:filename>')
def get_shop_image(filename):
    if not filename:
        abort(404)
    return send_from_directory(g.config.get('UPLOADED_SHOPIMAGES_DEST'), filename)
