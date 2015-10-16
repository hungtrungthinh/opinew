import os
from flask import request, redirect, url_for, render_template, flash, g, send_from_directory, \
    current_app, make_response, abort, session
from flask.ext.security import login_required, login_user, current_user, roles_required
from flask.ext.security.utils import encrypt_password
from providers.shopify_api import API
from webapp import db, review_photos
from webapp.client import client
from webapp.models import ShopProduct, Review, Shop, Platform, User, Product, Notification, Order, ShopProductReview, Role
from webapp.common import param_required, get_post_payload, catch_exceptions
from webapp.exceptions import ParamException, DbException
from webapp.forms import LoginForm, ExtendedRegisterForm, ReviewForm, ReviewPhotoForm
from config import Constants, basedir


@client.route('/install')
def install():
    """
    First step of the oauth process - generate address
    for permission grant from user
    :return:
    """
    ref = request.args.get('ref')
    if ref == 'internal':
        return install_internal_step_one()
    elif ref == 'shopify':
        return install_shopify_step_one()
    else:
        return install_internal_step_one()


def install_internal_step_one():
    return render_template('install/internal.html')


def install_shopify_step_one():
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

    nonce_request = param_required('state', request.args)
    hmac_request = param_required('hmac', request.args)
    shop_domain = param_required('shop', request.args)
    code = param_required('code', request.args)

    shop_name = shop_domain[:-14]

    # Initialize the API
    shopify_api = API(client_id, client_secret, shop_domain)
    shopify_api.initialize_api(nonce_request=nonce_request, hmac_request=hmac_request, code=code)

    # Get shop and products info from API
    shopify_shop = shopify_api.get_shop()
    shopify_products = shopify_api.get_products()

    # Create webhooks
    shopify_api.create_webhook("products/create",
                               "%s%s" % (g.config.get('OPINEW_API_SERVER'), url_for('api.create_product')))
    shopify_api.create_webhook("products/update",
                               "%s%s" % (g.config.get('OPINEW_API_SERVER'), url_for('api.update_product')))
    shopify_api.create_webhook("products/delete",
                               "%s%s" % (g.config.get('OPINEW_API_SERVER'), url_for('api.delete_product')))
    shopify_api.create_webhook("orders/create",
                               "%s%s" % (g.config.get('OPINEW_API_SERVER'), url_for('api.create_order')))
    shopify_api.create_webhook("fulfillments/create",
                               "%s%s" % (g.config.get('OPINEW_API_SERVER'), url_for('api.fulfill_order')))

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
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def user_setup():
    return render_template('shopify/user_setup.html')


@client.route('/')
def index():
    if current_user.is_authenticated():
        if current_user.has_role(Constants.ADMIN_ROLE):
            return redirect('/admin')
        elif current_user.has_role(Constants.SHOP_OWNER_ROLE):
            return redirect(url_for('.shop_admin'))
        if current_user.has_role(Constants.REVIEWER_ROLE):
            return redirect(url_for('.reviews'))
    return render_template('index.html')


@client.route('/customer_signup', methods=['GET', 'POST'])
def customer_signup():
    customer_signup_form = ExtendedRegisterForm()
    if customer_signup_form.validate_on_submit():
        # Stripe already has validated the card
        shop_owner = User.get_by_email_no_exception(email=customer_signup_form.email.data)
        if shop_owner:
            flash('User with email %s already exists. <a href="/reset">Forgot password?</a>')
            return render_template('customer_signup.html', customer_signup_form=customer_signup_form)
        shop_owner = User(email=customer_signup_form.email.data,
                          password=encrypt_password(customer_signup_form.password.data))
        shop_role = Role.query.filter_by(name=Constants.SHOP_OWNER_ROLE).first()
        shop_owner.roles.append(shop_role)
        shop_owner.stripe_token = param_required('stripe_token', request.form)
        shop = Shop()
        shop.owner = shop_owner
        db.session.add(shop)
        db.session.commit()
        login_user(shop_owner)
        return redirect(url_for('.install', ref='internal'))
    return render_template('customer_signup.html', customer_signup_form=customer_signup_form)


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
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def shop_admin():
    shop = current_user.shop
    return render_template('shop_admin/home.html', shop=shop)


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
        review_form = ReviewForm()
        review_photo_form = ReviewPhotoForm()
        signup_form = ExtendedRegisterForm()
        login_form = LoginForm()
        shop_id = param_required('shop_id', request.args)
        platform_product_id = param_required('platform_product_id', request.args)
        shop_product = ShopProduct.get_by_shop_and_platform_product_id(shop_id, platform_product_id)
        product = shop_product.product
        shop = shop_product.shop
        reviews = Review.get_for_product_approved_by_shop(product.id, shop.id)
        own_reviews = current_user.get_own_reviews_about_product_in_shop(product, shop) if current_user and current_user.is_authenticated() else []
        next_arg = request.url
    except (ParamException, DbException) as e:
        return '', 500
    return render_template('plugin/plugin.html', product=product, reviews=reviews,
                           signup_form=signup_form, login_form=login_form, review_form=review_form,
                           review_photo_form=review_photo_form, shop=shop, next_arg=next_arg,
                           own_reviews=own_reviews)


@client.route('/product', defaults={'product_id': 0})
@client.route('/product/<int:product_id>')
def get_product(product_id):
    try:
        product = Product.get_by_id(product_id)
        reviews = Review.get_for_product(product_id)
    except (ParamException, DbException) as e:
        flash(e.message)
        return redirect(request.referrer)
    return render_template('product/product.html', page_title="%s Reviews - " % product.name,
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
@catch_exceptions
def get_notifications():
    notifications = Notification.get_for_user(current_user)
    return render_template('client/notifications.html', notifications=notifications)


@client.route('/read_notification')
@login_required
@catch_exceptions
def read_notification():
    notification_id = param_required('id', request.args)
    next = param_required('next', request.args)
    notification = Notification.get_by_id(notification_id)
    notification.read()
    return redirect(next)


@client.route('/add_review', methods=['GET', 'POST'])
@login_required
@catch_exceptions
def web_review():
    order_id = request.args.get('order_id')
    product_id = request.args.get('product_id')
    order, product, products = None, None, None
    if product_id:
        product = Product.get_by_id(product_id)
    if not product:
        products = Product.query.all()
    if order_id:
        order = Order.get_by_id(order_id)
        if not order:
            flash('Not such order.')
            return redirect(url_for('.home'))
    if order_id and product not in order.products:
        flash('Product not in orders.')
        return redirect(url_for('.home'))
    if order_id and not order.user == current_user:
        flash('Not your order to review.')
        return redirect(url_for('.home'))
    review_form = ReviewForm()
    review_photo_form = ReviewPhotoForm()
    if request.method == 'POST' and review_form.validate_on_submit():
        try:
            payload = get_post_payload()
            body = payload.get('body', None)
            shop_id = param_required('shop_id', payload)
            photo_url = ''
            if 'photo' in request.files:
                photo_url = review_photos.save(request.files['photo'])

            if not body and not photo_url:
                raise ParamException('At least one of body or photo need to be provided.', 400)
        except ParamException as e:
            flash(e.message)
            return redirect(url_for('.home'))

        product.add_review(order=order, body=body, photo_url=photo_url, shop_id=shop_id)

        flash('Review submitted')
        if not order_id:
            return redirect(request.referrer)
        return redirect(request.args.get('next') or url_for('.reviews'))
    return render_template('web_review/main.html', order=order, product=product, products=products,
                           review_form=review_form, review_photo_form=review_photo_form)

@client.route('/product', defaults={'review_id': 0})
@client.route('/review/<int:review_id>')
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def view_review(review_id):
    review = Review.get_by_id(review_id)
    return render_template('shop_admin/view_review.html', review=review)


@client.route('/approve_review/<int:review_id>/<int:vote>', methods=['POST'])
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
@catch_exceptions
def approve_review(review_id, vote):
    review = Review.get_by_id(review_id)
    shop_review = ShopProductReview.get_by_shop_and_review_id(review.shop_product.shop.id, review_id)
    if vote == 1:
        shop_review.approve()
        flash('review approved')
    elif vote == 0:
        shop_review.disapprove()
        flash('review disapproved')
    return redirect(request.referrer)


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
        if "GET" in rule.methods and len(rule.arguments) == 0\
                and '/admin/' not in rule.rule:
            pages.append([rule.rule])
    sitemap_xml = render_template('sitemap.xml', pages=pages)
    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"
    return response


@client.route('/render_email', defaults={'filename': None})
@client.route('/render_email/<path:filename>')
def render_email(filename):
    if not filename or not g.mode == 'development':
        abort(404)
    return render_template('email/%s' % filename,
                           **{k: (w[0] if len(w) else w) for k, w in dict(request.args).iteritems()})
