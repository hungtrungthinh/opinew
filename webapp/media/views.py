from flask import send_from_directory, g, request, url_for, jsonify, abort
from webapp.media import media
from webapp import review_photos, user_photos


@media.route('/user/upload', methods=['POST'])
def upload_user_photo():
    if 'photo' in request.files:
        filename = user_photos.save(request.files['photo'])
        return jsonify({'photo_url': filename})
    return '', 400

@media.route('/user/', defaults={'filename': None})
@media.route('/user/<path:filename>')
def get_user_photo(filename):
    if not filename:
        abort(404)
    return send_from_directory(g.config.get('UPLOADED_USERPHOTOS_DEST'), filename)


@media.route('/review/upload', methods=['POST'])
def upload_review_photo():
    if 'photo' in request.files:
        filename = review_photos.save(request.files['photo'])
        return jsonify({'photo_url': filename})
    return '', 400


@media.route('/review/', defaults={'filename': None})
@media.route('/review/<path:filename>')
def get_review_photo(filename):
    if not filename:
        abort(404)
    return send_from_directory(g.config.get('UPLOADED_REVIEWPHOTOS_DEST'), filename)
