import os
from flask import request, redirect, url_for, render_template, flash, g, send_from_directory, \
    current_app, make_response, abort
from flask.ext.security import login_required, login_user, current_user
from providers.shopify_api import API
from webapp import db, review_photos
from webapp.client import client
from webapp.models import ShopProduct, Review, Shop, Platform, User, Product, Notification, Order, ShopProductReview
from webapp.common import param_required, get_post_payload, catch_exceptions
from webapp.exceptions import ParamException, DbException
from webapp.forms import LoginForm, SignupForm, ReviewForm
from config import Constants, basedir


@client.route('/install')
@catch_exceptions
def install():
    """
    First step of the oauth process - generate address
    for permission grant from user
    :return:
    """
    ref = param_required('ref', request.args)
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
# @shop_owner_required
@login_required
def user_setup():
    return render_template('shopify/user_setup.html')


@client.route('/')
def index():
    if current_user.is_authenticated():
        if current_user.has_role(Constants.REVIEWER_ROLE):
            return redirect(url_for('.reviews'))
        elif current_user.has_role(Constants.SHOP_OWNER_ROLE):
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
# @shop_owner_required
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
        signup_form = SignupForm()
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
                           signup_form=signup_form, login_form=login_form, review_form=review_form,
                           shop=shop, next_arg=next_arg)


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


@client.route('/read_notification')
@login_required
@catch_exceptions
def read_notification():
    notification_id = param_required('id', request.args)
    next = param_required('next', request.args)
    notification = Notification.get_by_id(notification_id)
    notification.read()
    return redirect(next)


@client.route('/review/<int:order_id>/<int:product_id>', methods=['GET', 'POST'])
# @reviewer_required
@login_required
@catch_exceptions
def web_review(order_id, product_id):
    order = None
    product = Product.get_by_id(product_id)
    if order_id:
        order = Order.get_by_id(order_id)
        if not order:
            flash('Not such order.')
            return redirect(url_for('.home'))
    if not product:
        flash('Not such product.')
        return redirect(url_for('.home'))
    if order_id and product not in order.products:
        flash('Product not in orders.')
        return redirect(url_for('.home'))
    if order_id and not order.user == current_user:
        flash('Not your order to review.')
        return redirect(url_for('.home'))
    review_form = ReviewForm()
    if request.method == 'POST' and review_form.validate_on_submit():
        try:
            payload = get_post_payload()
            body = payload.get('body', None)
            shop_id = param_required('shop_id', payload)
            photo_url = ''
            if 'photo' in request.files:
                photo_url = review_photos.save(request.files['photo'])
            tag_ids = request.values.getlist('tag_id')

            if not body and not tag_ids and not photo_url:
                raise ParamException('At least one of body, photo or tags need to be provided.', 400)
        except ParamException as e:
            flash(e.message)
            return redirect(url_for('.home'))

        product.add_review(order=order, body=body, photo_url=photo_url, tag_ids=tag_ids, shop_id=shop_id)

        flash('Review submitted')
        if not order_id:
            return redirect(request.referrer)
        return redirect(request.args.get('next') or url_for('.reviews'))
    return render_template('web_review/main.html', order=order, product=product, review_form=review_form)


@client.route('/review/<int:review_id>')
# @shop_owner_required
@login_required
def view_review(review_id):
    review = Review.get_by_id(review_id)
    return render_template('shop_admin/view_review.html', review=review)


@client.route('/approve_review/<int:review_id>/<int:vote>', methods=['POST'])
# @shop_owner_required
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
        if "GET" in rule.methods and len(rule.arguments) == 0:
            pages.append([rule.rule])
    sitemap_xml = render_template('sitemap.xml', pages=pages)
    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"
    return response


@client.route('/render_email/<filename>')
def render_email(filename):
    if not g.mode == 'development':
        abort(404)
    return render_template('email/%s' % filename,
                           **{k: (w[0] if len(w) else w) for k, w in dict(request.args).iteritems()})
