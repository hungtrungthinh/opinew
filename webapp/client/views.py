import os
from flask import request, jsonify, redirect, url_for, render_template, flash, g, send_from_directory, session, \
    current_app, make_response
from flask.ext.login import login_required, login_user, current_user, logout_user
from providers.shopify_api import API
from webapp import db, login_manager, review_photos
from webapp.client import client
from webapp.models import ShopProduct, Review, Shop, Platform, User, Product, Notification, Order, Business
from webapp.common import shop_owner_required, reviewer_required, param_required, get_post_payload, catch_exceptions
from webapp.exceptions import ParamException, DbException
from webapp.forms import LoginForm, SignupForm, ReviewForm, BusinessSignupForm
from config import Constants, basedir


@client.before_request
def before_request():
    g.constants = Constants
    g.config = current_app.config
    g.mode = current_app.config.get('MODE')


login_manager.login_view = "client.login"


@client.route('/install')
@catch_exceptions
def install():
    """
    First step of the oauth process - generate address
    for permission grant from user
    :return:
    """
    shop_domain = request.args.get('shop')
    if not len(shop_domain) > 14:
        raise ParamException('invalid shop domain', 400)
    shop_domain_ends_in = shop_domain[-14:]
    shop_name = shop_domain[:-14]
    if not shop_domain_ends_in or not shop_domain_ends_in == '.myshopify.com':
        raise ParamException('incorrect shop name', 400)
    shop = Shop.get_by_shop_domain(shop_domain)
    if shop and shop.access_token:
        return redirect(url_for('.user_setup'))

    client_id = g.config.get('SHOPIFY_APP_API_KEY')
    scopes = g.config.get('SHOPIFY_APP_SCOPES')

    nonce = shop_name

    redirect_uri = '%s/oauth/callback' % g.config.get('OPINEW_API_SERVER')

    url = 'https://{shop}/admin/oauth/authorize' \
          '?client_id={api_key}' \
          '&scope={scopes}' \
          '&redirect_uri={redirect_uri}' \
          '&state={nonce}'.format(
        shop=shop_domain, api_key=client_id, scopes=scopes, redirect_uri=redirect_uri, nonce=nonce)
    return redirect(url)


@client.route('/oauth/callback')
@catch_exceptions
def shopify_plugin_callback():
    """
    Seconds step of the oauth process - verify callback and
    send request for an access token
    :return:
    """
    client_id = g.config.get('SHOPIFY_APP_API_KEY')
    client_secret = g.config.get('SHOPIFY_APP_SECRET')

    nonce_request = request.args.get('state')
    hmac_request = request.args.get('hmac')
    shop_domain = request.args.get('shop')
    shop_name = shop_domain[:-14]
    code = request.args.get('code')

    # Initialize the API
    shopify_api = API(client_id, client_secret, shop_domain)
    shopify_api.initialize_api(nonce_request=nonce_request, hmac_request=hmac_request, code=code)

    # Get shop and products info from API
    shopify_shop = shopify_api.get_shop()
    shopify_products = shopify_api.get_products()

     # Create webhooks
    shopify_api.create_webhook("products/create", "%s%s" % (g.config.get('OPINEW_API_SERVER'), url_for('api.create_product')))
    shopify_api.create_webhook("products/update", "%s%s" % (g.config.get('OPINEW_API_SERVER'), url_for('api.update_product')))
    shopify_api.create_webhook("products/delete", "%s%s" % (g.config.get('OPINEW_API_SERVER'), url_for('api.delete_product')))
    shopify_api.create_webhook("orders/create", "%s%s" % (g.config.get('OPINEW_API_SERVER'), url_for('api.create_order')))
    shopify_api.create_webhook("fulfillments/create", "%s%s" % (g.config.get('OPINEW_API_SERVER'), url_for('api.fulfill_order')))

    # Create db records
    # Create shop user, generate pass
    shop_owner = User(email=shopify_shop.get('email', ''),
                      name=shopify_shop.get('shop_owner', ''),
                      role=Constants.SHOP_OWNER_ROLE)
    db.session.add(shop_owner)

    # Create shop with owner = shop_user
    shopify_platform = Platform.get_by_name('shopify')
    shop = Shop(label=shop_name, domain=shop_domain, platform=shopify_platform, access_token=shopify_api.access_token,
                owner=shop_owner)
    db.session.add(shop)

    # Import shop products
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


@client.route('/')
def index():
    if current_user.is_authenticated():
        if current_user.role == Constants.REVIEWER_ROLE:
            return redirect(url_for('.reviews'))
        elif current_user.role == Constants.SHOP_OWNER_ROLE:
            return redirect(url_for('.shop_admin'))
    return render_template('index.html')


@client.route('/reviews')
def reviews():
    page = request.args.get('page', '1')
    page = int(page) if page.isdigit() else 1
    start = Constants.REVIEWS_PER_PAGE * (page - 1)
    end = start + Constants.REVIEWS_PER_PAGE
    reviews = Review.get_latest(start, end)
    return render_template('reviewer/home.html', page_title="Reviews - ",
                           reviews=reviews, page=page)


@client.route('/shop_admin')
@shop_owner_required
@login_required
def shop_admin():
    shop = current_user.shop
    return render_template('shop_admin/home.html', shop=shop)

@client.route('/signup', methods=['GET', 'POST'])
def signup():
    business_signup_form = BusinessSignupForm()
    if business_signup_form.validate_on_submit():
        business = Business(**{k: v[0] for k, v in request.form.iteritems() if len(v) > 0})
        db.session.add(business)
        db.session.commit()
        session['business_signed_up'] = True
    return render_template('signup.html', business_signup_form=business_signup_form)


@client.route('/signup_user', methods=['GET', 'POST'])
def signup_user():
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
        return redirect(next_param or url_for('.index'))
    return render_template('login.html', login_form=login_form)


@client.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('.index'))


@client.route('/logout_from_plugin', methods=['GET'])
@login_required
def logout_from_plugin():
    logout_user()
    return redirect(request.referrer)

@client.route('/plugin')
def get_plugin():
    # TODO: Graceful degradation - try js first
    # <div id="opinew-reviews"></div>
    # <script src="http://opinew_api.local:5000/widgets/widget.js"></script>
    # <noscript>
    #     <iframe style="border:0; width:100%; height:600px;"
    #             src="http://opinew_api.local:5000/plugin?platform_product_id={{ product.id }}">
    #     </iframe>
    #     <p><a href="http://opinew_api.local:5000/">This widget provided by example.com</a></p>
    # </noscript>
    try:
        business_signup_form = BusinessSignupForm()
        login_form = LoginForm()
        platform_product_id = param_required('platform_product_id', request.args)
        shop_product = ShopProduct.get_by_platform_product_id(platform_product_id)
        product = shop_product.product
        shop = shop_product.shop
        reviews = Review.get_for_product_approved_by_shop(product.id, shop.id)
        next_arg = request.url
    except (ParamException, DbException) as e:
        return '', 500
    return render_template('plugin/plugin.html', product=product, reviews=reviews,
                           business_signup_form=business_signup_form,
                           login_form=login_form, next_arg=next_arg)


@client.route('/product/<int:product_id>')
def get_product(product_id):
    try:
        product = Product.get_by_id(product_id)
        reviews = Review.get_for_product(product_id)
    except (ParamException, DbException) as e:
        flash(e.message)
        return redirect(request.referrer)
    return render_template('product/product.html', page_title="%s Reviews - " % product.label,
                           product=product, reviews=reviews)


@client.route('/product/clickthrough')
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
@catch_exceptions
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
        return redirect(request.args.get('next') or url_for('.reviews'))
    return render_template('web_review/main.html', order=order, product=product, review_form=review_form)


@client.route('/review/<int:review_id>')
@shop_owner_required
@login_required
def view_review(review_id):
    review = Review.get_by_id(review_id)
    return render_template('shop_admin/view_review.html', review=review)


@client.route('/media/user/<path:filename>')
def media_user(filename):
    return send_from_directory(g.config.get('UPLOADED_USERPHOTOS_DEST'), filename)


@client.route('/media/review/<path:filename>')
def media_review(filename):
    return send_from_directory(g.config.get('UPLOADED_REVIEWPHOTOS_DEST'), filename)


@client.route('/faq')
def faq():
    return render_template('faq.html')


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
