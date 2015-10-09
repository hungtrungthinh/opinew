from flask import send_from_directory, g, request, url_for, jsonify, current_app
from webapp.media import media
from webapp import review_photos, user_photos
from config import Constants


@media.route('/user/upload')
def upload_user_photo():
    if 'photo' in request.files:
        filename = user_photos.save(request.files['photo'])
        return jsonify({'photo_url': url_for('.get_user_photo', filename=filename)})
    return '', 400


@media.route('/user/<path:filename>')
def get_user_photo(filename):
    return send_from_directory(g.config.get('UPLOADED_USERPHOTOS_DEST'), filename)


@media.route('/review/upload')
def upload_review_photo():
    if 'photo' in request.files:
        filename = review_photos.save(request.files['photo'])
        return jsonify({'photo_url': url_for('.get_review_photo', filename=filename)})
    return '', 400


@media.route('/review/<path:filename>')
def get_review_photo(filename):
    return send_from_directory(g.config.get('UPLOADED_REVIEWPHOTOS_DEST'), filename)
