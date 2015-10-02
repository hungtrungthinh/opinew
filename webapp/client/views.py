import os
import datetime
from flask import request, jsonify, redirect, url_for, render_template, flash, g, send_from_directory, session, \
    current_app, make_response
from flask.ext.login import login_required, login_user, current_user, logout_user
from providers.shopify_api import API
from webapp import db, login_manager, review_photos
from webapp.client import client
from webapp.models import ShopProduct, Review, Shop, Platform, User, Product, Notification, Order, Business
from webapp.common import shop_owner_required, reviewer_required, param_required, get_post_payload
from webapp.exceptions import ParamException, DbException
from webapp.forms import LoginForm, SignupForm, ReviewForm, BusinessSignupForm
from config import Config, Constants, basedir


@client.before_request
def before_request():
    g.config = Config
    g.mode = current_app.config.get('MODE')


login_manager.login_view = "client.login"


@client.route('/install')
def install():
    """
    First step of the oauth process - generate address
    for permission grant from user
    :return:
    """
    shop_domain = request.args.get('shop')
    shop_name = shop_domain[-14:]
    if not shop_domain or not shop_name == '.myshopify.com':
        return jsonify({'error': 'incorrect shop name'}), 400

    try:
        shop = Shop.get_by_shop_domain(shop_domain)
        if shop and shop.access_token:
            return redirect(url_for('.user_setup'))
    except DbException as e:
        pass

    client_id = Config.SHOPIFY_APP_API_KEY
    scopes = Config.SHOPIFY_APP_SCOPES

    nonce = shop_name

    redirect_uri = Config.SHOPIFY_OAUTH_CALLBACK

    url = 'https://{shop}/admin/oauth/authorize' \
          '?client_id={api_key}' \
          '&scope={scopes}' \
          '&redirect_uri={redirect_uri}' \
          '&state={nonce}'.format(
        shop=shop_domain, api_key=client_id, scopes=scopes, redirect_uri=redirect_uri, nonce=nonce)
    return redirect(url)


@client.route('/oauth/callback')
def shopify_plugin_callback():
    """
    Seconds step of the oauth process - verify callback and
    send request for an access token
    :return:
    """
    client_id = Config.SHOPIFY_APP_API_KEY
    client_secret = Config.SHOPIFY_APP_SECRET

    nonce_request = request.args.get('state')
    hmac_request = request.args.get('hmac')
    shop_domain = request.args.get('shop')
    shop_name = shop_domain[:-14]
    code = request.args.get('code')

    shopify_api = API(client_id, client_secret, shop_domain)
    shopify_api.initialize_api(nonce_request=nonce_request, hmac_request=hmac_request, code=code)

    # Create db records
    # Create shop with owner = shop_user
    shopify_platform = Platform.get_by_name('shopify')
    shop = Shop(label=shop_name, domain=shop_domain, platform=shopify_platform, access_token=shopify_api.access_token)

    # Create shop user, generate pass
    shopify_shop = shopify_api.get_shop()
    shop_owner = User(email=shopify_shop.get('email', ''),
                      name=shopify_shop.get('shop_owner', ''),
                      role=Constants.SHOP_OWNER_ROLE)
    shop.owner = shop_owner
    db.session.add(shop)

    # Create webhooks
    shopify_api.create_webhook("products/create", "%s%s" % (Config.OPINEW_API_SERVER, url_for('api.create_product')))
    shopify_api.create_webhook("products/update", "%s%s" % (Config.OPINEW_API_SERVER, url_for('api.update_product')))
    shopify_api.create_webhook("products/delete", "%s%s" % (Config.OPINEW_API_SERVER, url_for('api.delete_product')))
    shopify_api.create_webhook("orders/create", "%s%s" % (Config.OPINEW_API_SERVER, url_for('api.create_order')))
    shopify_api.create_webhook("fulfillments/create", "%s%s" % (Config.OPINEW_API_SERVER, url_for('api.fulfill_order')))

    # Import shop products
    shopify_products = shopify_api.get_products()
    for product_j in shopify_products:
        product = Product(label=product_j.get('title', ''))
        product_url = "https://%s/products/%s" % (shop_domain, product_j.get('handle', ''))
        shop_product = ShopProduct(product=product,
                                   shop=shop,
                                   url=product_url,
                                   platform_product_id=product_j.get('id', ''))
        db.session.add(shop_product)
    db.session.commit()

    # Login shop_user
    login_user(shop_owner)
    return redirect(url_for('.user_setup'))


@client.route('/user_setup')
@shop_owner_required
@login_required
def user_setup():
    return render_template('shopify/user_setup.html')


@client.route('/', methods=['GET', 'POST'])
def index():
    business_signup_form = BusinessSignupForm()
    if business_signup_form.validate_on_submit():
        business = Business(**{k: v[0] for k, v in request.form.iteritems() if len(v) > 0})
        db.session.add(business)
        db.session.commit()
        flash('Thanks for you interest.')
        session['business_signed_up'] = True
    return render_template('index.html', business_signup_form=business_signup_form)


@client.route('/home')
def home():
    reviews = Review.get_latest(10)
    if current_user.is_authenticated():
        if current_user.role == Constants.REVIEWER_ROLE:
            return render_template('reviewer/home.html', reviews=reviews)
        elif current_user.role == Constants.SHOP_OWNER_ROLE:
            shop = current_user.shop
            return render_template('shop_admin/home.html', shop=shop)
    return render_template('reviewer/home.html', reviews=reviews)


@client.route('/faq')
def faq():
    return render_template('faq.html')


@client.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated():
        return redirect(request.referrer or url_for('.shop_admin'))
    signup_form = SignupForm()
    if signup_form.validate_on_submit():
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        registered_user = User.query.filter_by(email=email).first()
        if registered_user:
            flash('User with email %s already exist.' % email)
            return redirect(url_for('.signup'))
        user = User(email=email, password=password, name=name, role=Constants.REVIEWER_ROLE)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        next_param = request.form.get('next')
        return redirect(next_param or url_for('.home'))
    return render_template('signup.html', signup_form=signup_form)


@client.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated():
        return redirect(request.referrer or url_for('.shop_admin'))
    login_form = LoginForm()
    if login_form.validate_on_submit():
        email = request.form.get('email')
        password = request.form.get('password')
        registered_user = User.query.filter_by(email=email).first()
        if not registered_user:
            flash('User with email %s does not exist.' % email)
            return redirect(url_for('.login'))
        try:
            registered_user.validate_password(password)
        except DbException as e:
            flash(e.message)
            return render_template('login.html', login_form=login_form)
        login_user(registered_user)
        next_param = request.form.get('next')
        return redirect(next_param or url_for('.home'))
    return render_template('login.html', login_form=login_form)


@client.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('.home'))


@client.route('/plugin')
def get_plugin():
    try:
        platform_product_id = param_required('platform_product_id', request.args)
        shop_product = ShopProduct.get_by_platform_product_id(platform_product_id)
        product = shop_product.product
        shop = shop_product.shop
        reviews = Review.get_for_product_approved_by_shop(product.id, shop.id)
    except (ParamException, DbException) as e:
        return jsonify({"error": e.message}), e.status_code
    return render_template('plugin/shopify.html', product=product.serialize_with_reviews(reviews))


@client.route('/products/<int:product_id>')
def get_product(product_id):
    try:
        product = Product.get_by_id(product_id)
        reviews = Review.get_for_product(product_id)
    except (ParamException, DbException) as e:
        return jsonify({"error": e.message}), e.status_code
    return render_template('product/main.html', product=product.serialize_with_reviews(reviews))


@client.route('/products/clickthrough')
def clickthrough_product():
    """
    Create a clickthrough record
    """
    try:
        platform_product_id = param_required('platform_product_id', request.args)
        shop_product = ShopProduct.get_by_platform_product_id(platform_product_id)
        url = shop_product.url
    except (ParamException, DbException) as e:
        flash(e.message)
        return redirect(request.referrer)
    return redirect(url)


@client.route('/notifications')
@login_required
def get_notifications():
    notifications = Notification.get_for_user(current_user)
    return render_template('client/notifications.html', notifications=notifications)


@client.route('/review/<int:order_id>/<int:product_id>', methods=['GET', 'POST'])
@reviewer_required
@login_required
def web_review(order_id, product_id):
    order = Order.get_by_id(order_id)
    product = Product.get_by_id(product_id)
    if not order:
        flash('Not such order.')
        return redirect(url_for('.home'))
    if not product:
        flash('Not such product.')
        return redirect(url_for('.home'))
    if product not in order.products:
        flash('Product not in orders.')
        return redirect(url_for('.home'))
    if not order.user == current_user:
        flash('Not your order to review.')
        return redirect(url_for('.home'))
    review_form = ReviewForm()
    if request.method == 'POST' and review_form.validate_on_submit():
        try:
            payload = get_post_payload()
            body = payload.get('body', None)
            photo_url = ''
            if 'photo' in request.files:
                photo_url = review_photos.save(request.files['photo'])
            tag_ids = request.values.getlist('tag_id')

            if not body and not tag_ids and not photo_url:
                raise ParamException('At least one of body, photo or tags need to be provided.', 400)
        except ParamException as e:
            flash(e.message)
            return redirect(url_for('.home'))

        product.add_review(order=order, body=body, photo_url=photo_url, tag_ids=tag_ids)

        flash('Review submitted')
        return redirect(url_for('.home'))
    return render_template('web_review/main.html', order=order, product=product, review_form=review_form)


@client.route('/view_review/<int:review_id>')
@shop_owner_required
@login_required
def view_review(review_id):
    review = Review.get_by_id(review_id)
    return render_template('shop_admin/view_review.html', review=review)


@client.route('/media/user/<path:filename>')
def media_user(filename):
    return send_from_directory(Config.UPLOADED_USERPHOTOS_DEST, filename)


@client.route('/media/review/<path:filename>')
def media_review(filename):
    return send_from_directory(Config.UPLOADED_REVIEWPHOTOS_DEST, filename)


@client.route('/about_us')
def about_us():
    return render_template('about_us.html', page_title="About us - ")


@client.route('/support')
def support():
    return render_template('support.html', page_title="Support - ")


@client.route('/terms')
def terms_of_use():
    return render_template('terms_of_use.html', page_title="Terms of Use - ")


@client.route('/privacy')
def privacy_policy():
    return render_template('privacy_policy.html', page_title="Privacy Policy - ")


@client.route('/robots.txt')
def robotstxt():
    return send_from_directory(os.path.join(basedir, 'webapp', 'static', 'txt'), 'robots.txt')


@client.route('/humans.txt')
def humanstxt():
    return send_from_directory(os.path.join(basedir, 'webapp', 'static', 'txt'), 'humans.txt')


@client.route('/favicon.ico')
def faviconico():
    return send_from_directory(os.path.join(basedir, 'webapp', 'static', 'icons'), 'opinew32.ico')


@client.route('/sitemap.xml')
def sitemapxml():
    """Generate sitemap.xml. Makes a list of urls and date modified."""
    pages = []
    # static pages
    for rule in current_app.url_map.iter_rules():
        if "GET" in rule.methods and len(rule.arguments) == 0:
            pages.append([rule.rule])
    sitemap_xml = render_template('sitemap.xml', pages=pages)
    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"
    return response
