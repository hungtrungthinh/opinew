import requests
import time
import hashlib
from requests.auth import HTTPBasicAuth
from flask import render_template, send_from_directory, redirect, url_for, request, flash, jsonify, current_app
from flask.ext.login import login_required, current_user, login_user, logout_user
from webapp import login_manager
from webapp.forms import LoginForm, ReviewForm
from webapp.client import client
from webapp.models import Shop, User, Role, Order, Review, Callback
from webapp.common import validate_user_role, get_post_payload
from webapp.exceptions import ParamException
from config import Config

login_manager.login_view = "client.login"

@client.route('/product/<int:product_id>')
def view_product(product_id):
    r = requests.get("%s%s" %
                     (current_app.config.get('OPINEW_API_SERVER'), url_for('api.get_product_reviews', product_id=product_id)))
    product_reviews = r.json()
    return render_template('client/product.html', product_reviews=product_reviews)

@client.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated():
        return redirect(request.referrer or url_for('.shop_admin'))
    login_form = LoginForm()
    if login_form.validate_on_submit():
        email = request.form.get('email')
        registered_user = User.query.filter_by(email=email).first()
        if not registered_user:
            flash('User with email %s does not exist.' % email)
            return redirect(url_for('.login'))
        login_user(registered_user)
        next_param = request.form.get('next')
        return redirect(next_param or url_for('.shop_admin'))
    return render_template('login.html', login_form=login_form)


@login_required
@client.route('/logout', methods=['GET'])
def logout():
    logout_user()
    return redirect(url_for('.shop_admin'))


@client.route('/')
def home():
    reviews = Review.query.order_by(Review.created_ts.desc()).all()
    return render_template('client/home.html', reviews=reviews)


@client.route('/shop_admin')
@login_required
def shop_admin():
    role = Role.query.filter_by(name='SHOP').first()
    validate_user_role(role)
    shop = Shop.query.filter_by(owner_id=current_user.id).first()
    return render_template('shop_admin/home.html', shop=shop)


@client.route('/notify_for_review/<int:order_id>')
@login_required
def notify_for_review(order_id):
    role = Role.query.filter_by(name='SHOP').first()
    validate_user_role(role)
    shop_id = current_user.shop.id
    r = requests.patch("%s%s" %
                       (current_app.config.get('OPINEW_API_SERVER'), url_for('api.update_shop_order', shop_id=shop_id,
                                                                             order_id=order_id)),
                       auth=HTTPBasicAuth(current_user.email, current_user.password),
                       data={'action': 'notify'})
    return redirect(url_for('client.shop_admin'))


@client.route('/view_review/<int:review_id>')
@login_required
def view_review(review_id):
    role = Role.query.filter_by(name='SHOP').first()
    validate_user_role(role)
    r = requests.get("%s%s" %
                     (current_app.config.get('OPINEW_API_SERVER'), url_for('api.get_review', review_id=review_id)),
                     auth=HTTPBasicAuth(current_user.email, current_user.password))
    review = r.json()
    return render_template('shop_admin/view_review.html', review=review)


@client.route('/approve_review/<int:review_id>')
@login_required
def approve_review(review_id):
    role = Role.query.filter_by(name='SHOP').first()
    validate_user_role(role)
    shop_id = current_user.shop.id
    requests.patch("%s%s" %
                   (current_app.config.get('OPINEW_API_SERVER'),
                    url_for('api.approve_shop_product_review', shop_id=shop_id,
                            review_id=review_id)),
                   auth=HTTPBasicAuth(current_user.email, current_user.password),
                   data={'action': 'approve'})
    return redirect(url_for('client.shop_admin'))


@client.route('/disapprove_review/<int:review_id>')
@login_required
def disapprove_review(review_id):
    role = Role.query.filter_by(name='SHOP').first()
    validate_user_role(role)
    shop_id = current_user.shop.id
    requests.patch("%s%s" %
                   (current_app.config.get('OPINEW_API_SERVER'),
                    url_for('api.approve_shop_product_review', shop_id=shop_id,
                            review_id=review_id)),
                   auth=HTTPBasicAuth(current_user.email, current_user.password),
                   data={'action': 'disapprove'})
    return redirect(url_for('client.shop_admin'))


@client.route('/create_review/<int:order_id>', methods=['GET', 'POST'])
@login_required
def web_review(order_id):
    role = Role.query.filter_by(name='REVIEWER').first()
    validate_user_role(role)
    order = Order.query.filter_by(id=order_id).first()
    if not order:
        flash('Not such order.')
        return redirect(url_for('.home'))
    if not order.user == current_user:
        flash('Not your order to review.')
        return redirect(url_for('.home'))
    if order.review:
        flash('Review already posted')
        return redirect(url_for('.home'))
    review_form = ReviewForm()
    if request.method == 'POST' and review_form.validate_on_submit():
        try:
            payload = get_post_payload()
        except ParamException as e:
            return jsonify({"error": e.message}), 400
        f = {}
        if request.files['photo']:
            rf = request.files['photo']
            f = {'photo': (rf.filename, rf.stream, rf.content_type, dict(rf.headers))}
        requests.post("%s%s" %
                      (current_app.config.get('OPINEW_API_SERVER'),
                       url_for('api.add_shop_product_review', shop_id=order.shop_id,
                               product_id=order.product_id)),
                      auth=HTTPBasicAuth(current_user.email, current_user.password),
                      files=f,
                      data=payload)
        flash('Review submitted')
        return redirect(url_for('.home'))
    return render_template('web_review/home.html', order=order, review_form=review_form)


@client.route('/plugin/shop/<int:shop_id>/product/<int:product_id>/reviews')
def plugin_product_reviews(shop_id, product_id):
    r = requests.get("%s%s" %
                     (current_app.config.get('OPINEW_API_SERVER'), url_for('api.get_shop_product_reviews_approved',
                                                                           shop_id=shop_id, product_id=product_id)))
    product = r.json()
    return render_template('plugin/plugin.html', product=product)


@client.route('/plugin/shopify')
def plugin_shopify_product_reviews():
    shop_product_id = request.args.get('shop_product_id')
    if not shop_product_id:
        return '', 404
    r1 = requests.get("%s%s" %
                      (current_app.config.get('OPINEW_API_SERVER'), url_for('api.get_shop_product_reviews_approved',
                                                                            shop_product_id=shop_product_id)))
    product_reviews = r1.json()
    return render_template('plugin/shopify.html', product=product_reviews)


@client.route('/notifications')
@login_required
def get_notifications():
    r = requests.get("%s%s" %
                     (current_app.config.get('OPINEW_API_SERVER'), url_for('api.get_notifications')),
                     auth=HTTPBasicAuth(current_user.email, current_user.password))
    notifications = r.json()
    return render_template('client/notifications.html', notifications=notifications)


@client.route('/notifications/<int:notification_id>')
@login_required
def follow_notification(notification_id):
    r = requests.patch("%s%s" %
                       (current_app.config.get('OPINEW_API_SERVER'),
                        url_for('api.update_notification', notification_id=notification_id)),
                       auth=HTTPBasicAuth(current_user.email, current_user.password),
                       data={'action': 'read'})
    notification = r.json()
    if not notification:
        flash('Wrong notification')
        return redirect(url_for('.home'))
    return redirect(notification['url'])


@client.route('/media/user/<path:filename>')
def media_user(filename):
    return send_from_directory(Config.UPLOADED_USERPHOTOS_DEST, filename)


@client.route('/media/review/<path:filename>')
def media_review(filename):
    return send_from_directory(Config.UPLOADED_REVIEWPHOTOS_DEST, filename)


@client.route('/shopify/install')
@login_required
def shopify_plugin_install():
    shop = current_user.shop
    if not shop:
        flash('current user is not an owner of shop')
        return redirect(url_for('client.home'))
    nonce = time.time() * 42
    callback = Callback(nonce)

    shop = request.args.get('shop', 'opinew.myshopify.com')
    if not shop[-14:] == '.myshopify.com':
        return jsonify({'error': 'incorrect shop name'})
    api_key = '7260cb38253b9adc4af0c90eb622f4ce'
    scopes = 'read_products,read_orders,read_fulfillments'
    redirect_uri = 'http://162.13.140.76/shopify/callback/%s' % callback.id

    url = 'https://{shop}/admin/oauth/authorize?client_id={api_key}&scope={scopes}&redirect_uri={redirect_uri}&state={nonce}'.format(
        shop=shop, api_key=api_key, scopes=scopes, redirect_uri=redirect_uri, nonce=nonce)
    return redirect(url)


@client.route('/shopify/callback/<int:callback_id>')
@login_required
def shopify_plugin_callback(callback_id):
    shop = current_user.shop
    if not shop:
        flash('current user is not an owner of shop')
        return redirect(url_for('client.home'))
    client_id = '7260cb38253b9adc4af0c90eb622f4ce'
    client_secret = '4aff6d82da2174ec13167f149ff7ee50'

    # verify nonce
    nonce = request.args.get('nonce')
    if not nonce:
        return jsonify({'error': 'no nonce'})
    callback = Callback.get_by_id(callback_id)
    callback_nonce = callback.nonce
    if not callback_nonce == nonce:
        return jsonify({'error': 'incorrect nonce'})

    # verify hmac
    hmac = request.args.get('hmac')
    if not hmac:
        return jsonify({'error': 'incorrect shop name'})
    hmac_message = "shop={shop}&timestamp={timestamp}".format(
        shop=request.args.get('shop').replace('%', '%25').replace('&', '%26'),
        timestamp=request.args.get('timestamp')
    )
    dig = hmac.new(client_secret, msg=hmac_message, digestmod=hashlib.sha256).digest()
    if not hmac == dig:
        return jsonify({'error': 'hmac unverified'})

    # verify shop name
    shop = request.args.get('shop', 'opinew.myshopify.com')
    if not shop[-14:] == '.myshopify.com':
        return jsonify({'error': 'incorrect shop name'})
    code = request.args.get('code')
    r = requests.post('https://{shop}.myshopify.com/admin/oauth/access_token'.format(shop=shop[:-14]),
                      data={'client_id': client_id, 'client_secret': client_secret, 'code': code})

    access_token = r.json().get('access_token')

    # TODO: use the access_token as a header to make api requests
    # X-Shopify-Access-Token: {access_token}
    shop.update_access_token(access_token)


@client.route('/shopify/complete')
@login_required
def shopify_plugin_complete():
    shop = current_user.shop
    if not shop:
        flash('current user is not an owner of shop')
        return redirect(url_for('client.home'))
    return render_template('shopify_complete.html', shop=shop)


@client.route('/shopify/import_products', methods=['POST'])
@login_required
def shopify_import_products():
    shop_id = request.form.get('shop_id')
    if not shop_id:
        flash('incorrect shop id')
        return redirect(url_for('client.shopify_plugin_complete'))
    r = requests.post("%s%s" %
                     (
                     current_app.config.get('OPINEW_API_SERVER'), url_for('api.create_shop_products', shop_id=shop_id)),
                     auth=HTTPBasicAuth(current_user.email, current_user.password), data={'batch': True})
    if r.json() == {}:
        flash('import success')
    return redirect(url_for('client.shopify_plugin_complete'))