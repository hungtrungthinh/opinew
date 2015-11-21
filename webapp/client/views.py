import datetime
import os
from werkzeug.datastructures import MultiDict
from flask import request, redirect, url_for, render_template, flash, g, send_from_directory, \
    current_app, make_response, abort, jsonify
from flask.ext.security import login_required, login_user, current_user, roles_required, logout_user
from flask.ext.security.utils import encrypt_password
from providers.shopify_api import API
from webapp import db
from webapp.client import client
from webapp.models import Review, Shop, Platform, User, Product, Order, \
    Role, Customer, Notification, Subscription, Plan, ReviewRequest, ProductUrl
from webapp.common import param_required, catch_exceptions, generate_temp_password, get_post_payload
from webapp.exceptions import ParamException, DbException
from webapp.forms import LoginForm, ReviewForm, ReviewImageForm, ShopForm, ExtendedRegisterForm, ReviewRequestForm
from config import Constants, basedir
from providers import giphy


@client.route('/install')
@catch_exceptions
def install():
    """
    First step of the oauth process - generate address
    for permission grant from user
    :return:
    """
    ref = request.args.get('ref')
    if ref == 'shopify':
        return install_shopify_step_one()
    return redirect('/register', **request.args)


def install_shopify_step_one():
    shop_domain = param_required('shop', request.args)
    if not len(shop_domain) > 14:
        raise ParamException('invalid shop domain', 400)
    shop_domain_ends_in = shop_domain[-14:]
    shop_name = shop_domain[:-14]
    if not shop_domain_ends_in or not shop_domain_ends_in == '.myshopify.com':
        raise ParamException('incorrect shop name', 400)
    shop = Shop.query.filter_by(domain=shop_domain).first()
    if shop and shop.access_token:
        return redirect(url_for('client.shop_dashboard'))

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
    shopify_orders = shopify_api.get_orders()

    # Create webhooks
    shopify_api.create_webhook("products/create",
                               "%s%s" % (g.config.get('OPINEW_API_SERVER'),
                                         url_for('api.platform_shopify_create_product')))
    shopify_api.create_webhook("products/update",
                               "%s%s" % (g.config.get('OPINEW_API_SERVER'),
                                         url_for('api.platform_shopify_update_product')))
    shopify_api.create_webhook("products/delete",
                               "%s%s" % (g.config.get('OPINEW_API_SERVER'),
                                         url_for('api.platform_shopify_delete_product')))
    shopify_api.create_webhook("orders/create",
                               "%s%s" % (g.config.get('OPINEW_API_SERVER'),
                                         url_for('api.platform_shopify_create_order')))
    shopify_api.create_webhook("fulfillments/create",
                               "%s%s" % (g.config.get('OPINEW_API_SERVER'),
                                         url_for('api.platform_shopify_fulfill_order')))

    # Create db records
    # Create shop user, generate pass
    shop_owner_email = shopify_shop.get('email', '')
    shop_owner = User.get_by_email_no_exception(shop_owner_email)
    shop_owner_role = Role.query.filter_by(name=Constants.SHOP_OWNER_ROLE).first()
    if not shop_owner:
        shop_owner_name = shopify_shop.get('shop_owner', '')
        temp_password = generate_temp_password()
        shop_owner = User(email=shop_owner_email,
                          temp_password=temp_password,
                          password=encrypt_password(temp_password),
                          name=shop_owner_name)

        from async import tasks

        tasks.send_email.delay(recipients=[shop_owner_email],
                               template='email/new_user.html',
                               template_ctx={'user_email': shop_owner_email,
                                             'user_temp_password': temp_password,
                                             'user_name': shop_owner_name
                                             },
                               subject="Welcome to Opinew!")
        shop_owner.roles.append(shop_owner_role)
        db.session.add(shop_owner)

        # Create shop with owner = shop_user
        shopify_platform = Platform.get_by_name('shopify')
        shop = Shop(name=shop_name,
                    domain=shop_domain,
                    platform=shopify_platform,
                    access_token=shopify_api.access_token,
                    owner=shop_owner)
        shop_owner.shops.append(shop)
        db.session.add(shop)

        # Import shop products
        for product_j in shopify_products:
            product_url = "https://%s/products/%s" % (shop_domain, product_j.get('handle', ''))
            product = Product(name=product_j.get('title', ''),
                              shop=shop,
                              platform_product_id=product_j.get('id', ''))
            product_url = ProductUrl(url=product_url)
            product.urls.append(product_url)
            db.session.add(product)
        db.session.commit()

        for order_j in shopify_orders:
            user_name = "%s %s" % (order_j.get('customer', {}).get('first_name'), order_j.get('customer', {}).get('last_name'))
            user, _ = User.get_or_create_by_email(email=order_j.get('email'), name=user_name)
            try:
                created_at_dt = datetime.datetime.strptime(order_j.get('created_at')[:-6], "%Y-%m-%dT%H:%M:%S")
            except:
                created_at_dt = datetime.datetime.utcnow()
            order = Order(
                purchase_timestamp=created_at_dt,
                platform_order_id=order_j.get('id'),
                shop_id=shop.id,
                user=user
            )
            if order_j.get('fulfillment_status'):
                order.status = Constants.ORDER_STATUS_SHIPPED
            if order_j.get('cancelled_at'):
                order.status = Constants.ORDER_STATUS_FAILED
            for product_j in order_j.get('line_items', []):
                product = Product.query.filter_by(platform_product_id=product_j.get('id')).first()
                if product:
                    order.products.append(product)
            db.session.add(order)
        db.session.commit()

        # Login shop_user
        login_user(shop_owner)
    return redirect(url_for('client.shop_dashboard'))

# Signals
from flask.ext.security import user_registered


def capture_registration(app, user=None, confirm_token=None):
    if user.is_shop_owner:
        # TODO: ASYNC (?)
        # append the role of a shop owner
        shop_role = Role.query.filter_by(name=Constants.SHOP_OWNER_ROLE).first()
        user.roles.append(shop_role)
        # create a customer account
        plan = Plan.query.filter_by(id=1).first()
        customer = Customer(user=user).create()
        subscription = Subscription(customer=customer, plan=plan).create()
        db.session.add(subscription)
    else:
        reviewer_role = Role.query.filter_by(name=Constants.REVIEWER_ROLE).first()
        user.roles.append(reviewer_role)
    db.session.commit()


user_registered.connect(capture_registration)


@client.route('/')
def index():
    if 'mobile' in g and g.mobile:
        login_form = LoginForm()
        if current_user.is_authenticated():
            return redirect(url_for('client.reviews'))
        return render_template('mobile_index.html', login_user_form=login_form)
    if current_user.is_authenticated():
        if current_user.has_role(Constants.ADMIN_ROLE):
            return redirect('/admin')
        elif current_user.has_role(Constants.SHOP_OWNER_ROLE):
            return redirect(url_for('client.shop_dashboard'))
        elif current_user.has_role(Constants.REVIEWER_ROLE):
            return redirect(url_for('client.reviews'))
    return render_template('index.html')


@client.route('/', defaults={'review_request_token': None})
@client.route('/<review_request_token>')
def get_by_review_request_token(review_request_token):
    review_request = ReviewRequest.query.filter_by(token=review_request_token).first()
    if review_request:
        return redirect(url_for('client.add_review', review_request_id=review_request.id,
                                review_request_token=review_request.token, **request.args))
    return redirect(url_for('client.index'))


@client.route('/reviews')
def reviews():
    page = request.args.get('page', '1')
    page = int(page) if page.isdigit() else 1
    start = Constants.REVIEWS_PER_PAGE * (page - 1)
    end = start + Constants.REVIEWS_PER_PAGE
    reviews = Review.get_latest(start, end)
    return render_template('reviews.html',
                           page_title="Reviews - Opinew",
                           page_description="Featured product reviews with images, videos, emojis, gifs and memes.",
                           reviews=reviews, page=page)


@client.route('/dashboard')
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def shop_dashboard():
    shop_form, platforms = None, None
    shops = current_user.shops
    if not shops:
        shop_form = ShopForm()
        platforms = Platform.query.all()
    if len(shops) == 1:
        return redirect(url_for('client.shop_dashboard_id', shop_id=shops[0].id))
    return render_template('shop_admin/choose_shop.html', shops=shops, shop_form=shop_form, platforms=platforms)


@client.route('/dashboard', defaults={'shop_id': 0})
@client.route('/dashboard/<int:shop_id>')
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def shop_dashboard_id(shop_id):
    shop = Shop.query.filter_by(owner_id=current_user.id, id=shop_id).first()
    if not shop:
        flash('Not your shop')
        return redirect(url_for('client.shop_dashboard'))
    if shop.platform and shop.platform.name == 'shopify':
        code = render_template('user_setup/shopify_code.html', shop=shop)
    else:
        code = render_template('user_setup/code.html', shop=shop)
    shop_form = ShopForm(MultiDict(shop.__dict__))
    review_request_form = ReviewRequestForm()
    platforms = Platform.query.all()
    return render_template('shop_admin/home.html', shop=shop, code=code, shop_form=shop_form,
                           review_request_form=review_request_form, platforms=platforms)


@client.route('/dashboard', defaults={'shop_id': 0})
@client.route('/dashboard/<int:shop_id>/orders')
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def shop_dashboard_orders(shop_id):
    shop = Shop.query.filter_by(owner_id=current_user.id, id=shop_id).first()
    if not shop:
        flash('Not your shop')
        return redirect(url_for('client.shop_dashboard'))
    orders = Order.query.filter_by(shop_id=shop_id).order_by(Order.purchase_timestamp.desc()).all()
    return render_template("shop_admin/orders.html", orders=orders)


@client.route('/dashboard', defaults={'shop_id': 0})
@client.route('/dashboard/<int:shop_id>/reviews')
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def shop_dashboard_reviews(shop_id):
    shop = Shop.query.filter_by(owner_id=current_user.id, id=shop_id).first()
    if not shop:
        flash('Not your shop')
        return redirect(url_for('client.shop_dashboard'))
    products = Product.query.filter_by(shop_id=shop_id).all()
    reviews = Review.query.filter(Review.product_id.in_([p.id for p in products])).all()
    return render_template("shop_admin/reviews.html", reviews=reviews)


@client.route('/plugin')
def get_plugin():
    try:
        review_form = ReviewForm()
        review_image_form = ReviewImageForm()
        signup_form = ExtendedRegisterForm()
        login_form = LoginForm()
        shop_id = param_required('shop_id', request.args)
        get_by = param_required('get_by', request.args)
        if get_by == 'url':
            product_url = param_required('product_url', request.args)
            product = Product.find_product_by_url(product_url, shop_id)
        elif get_by == 'platform_id':
            platform_product_id = param_required('platform_product_id', request.args)
            product = Product.query.filter_by(shop_id=shop_id, platform_product_id=platform_product_id).first()
        else:
            product = None
        if not product:
            return '', 404
        reviews = Review.query.filter_by(product_id=product.id, approved_by_shop=True).order_by(
            Review.created_ts.desc()).all()
        own_reviews = Review.query.filter_by(user=current_user,
                                             product=product).all() if current_user.is_authenticated() else []
        next_arg = request.url
        product.plugin_views += 1
        db.session.commit()
    except (ParamException, DbException, AssertionError) as e:
        return '', 404
    return render_template('plugin/plugin.html', product=product, reviews=reviews,
                           signup_form=signup_form, login_form=login_form, review_form=review_form,
                           review_image_form=review_image_form, next_arg=next_arg,
                           own_reviews=own_reviews, in_plugin=True)


@client.route('/product', defaults={'product_id': 0})
@client.route('/product/<int:product_id>')
def get_product(product_id):
    try:
        product = Product.get_by_id(product_id)
        reviews = Review.query.filter_by(product_id=product_id).order_by(
            Review.created_ts.desc()).all()
    except (ParamException, DbException) as e:
        flash(e.message)
        return redirect(request.referrer)
    return render_template('product.html', page_title="%s Reviews - " % product.name,
                           product=product, reviews=reviews)


@client.route('/get_order', defaults={'order_id': 0})
@client.route('/get_order/<int:order_id>')
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def get_order(order_id):
    shop = Shop.query.filter_by(owner_id=current_user.id).first()
    if not shop:
        flash('Not your shop')
        return redirect(url_for('client.shop_dashboard'))
    order = Order.get_by_id(order_id)
    return jsonify({'order_id': order.id})


@client.route('/read-notification')
@login_required
@catch_exceptions
def read_notification():
    notification_id = param_required('id', request.args)
    next = param_required('next', request.args)
    notification = Notification.get_by_id(notification_id)
    notification.read()
    return redirect(next)


@client.route('/add-review', methods=['GET'])
@catch_exceptions
@login_required
def add_review():
    """
    /add_review renders a form for logged in users to post a review.
    It accepts:
        * product_id (optional) - product for which the review shall be posted
        * review_request_id (optional) - Requested review for which review shall be posted
        * review_request_token (required if review_request_id) - token from a review_request
    """
    ctx = {}
    # Check if product_id is requested
    if 'product_id' in request.args:
        ctx['product'] = Product.query.filter_by(id=request.args.get('product_id')).first()
    # Check if it's a review request and that the correct token is there
    if 'review_request_id' in request.args and 'review_request_token' in request.args:
        review_request = ReviewRequest.query.filter_by(id=request.args.get('review_request_id')).first()
        if not review_request or not review_request.token == request.args.get('review_request_token'):
            flash('Incorrect review request token')
        else:
            ctx['product'] = review_request.for_product
    if 'product' not in ctx or not ctx['product']:
        ctx['products'] = Product.query.all()
    # Initialize forms
    ctx['review_image_form'] = ReviewImageForm()
    ctx['review_form'] = ReviewForm()
    return render_template('add_review.html', **ctx)


@client.route('/review', defaults={'review_id': 0})
@client.route('/review/<int:review_id>')
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def view_review(review_id):
    review = Review.query.filter_by(review_id)
    return render_template('shop_admin/view_review.html', review=review)


@client.route('/plugin-logout')
@login_required
def plugin_logout():
    logout_user()
    return redirect(request.referrer)


@client.route('/faq')
def faq():
    return render_template('faq.html')


@client.route('/about-us')
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
        if "GET" in rule.methods and len(rule.arguments) == 0 \
                and '/admin/' not in rule.rule:
            pages.append([rule.rule])
    sitemap_xml = render_template('sitemap.xml', pages=pages)
    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"
    return response


@client.route('/render-email', defaults={'filename': None})
@client.route('/render-email/<path:filename>')
def render_email(filename):
    if not filename:
        abort(404)
    review_request_id = request.args.get('review_request')
    review_request = ReviewRequest.query.filter_by(id=review_request_id).first()
    kwargs = {k: (w[0] if len(w) else w) for k, w in dict(request.args).iteritems()}
    kwargs['review_request'] = review_request
    return render_template('email/%s' % filename, **kwargs)


@client.route('/fake-shopify-api', defaults={'shop': None})
@client.route('/fake-shopify-api/<shop>', methods=['POST'])
def fake_shopify_api(shop):
    if not g.mode == 'testing':
        abort(404)
    return jsonify({'access_token': 'hello world'}), 200


@client.route('/search-giphy')
def search_giphy():
    giphy_api_key = current_app.config.get('GIPHY_API_KEY')
    query = request.args.get('q')
    if not query:
        return jsonify(giphy.get_trending(giphy_api_key))
    limit = request.args.get('limit', Constants.REVIEWS_PER_PAGE)
    offset = request.args.get('offset', 0)
    return jsonify(giphy.get_by_query(giphy_api_key, query, limit, offset))


@client.route('/update-order', methods=['POST'])
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def update_order():
    post = get_post_payload()
    order_id = param_required('order_id', post)
    state = param_required('state', post)
    shops = Shop.query.filter_by(owner_id=current_user.id).all()
    order = Order.query.filter_by(id=order_id).first()
    failure, delete = False, False
    if order.shop_id not in [s.id for s in shops]:
        flash('Not your shop')
        failure = True
    if state == Constants.ORDER_STATUS_SHIPPED:
        order.ship()
        db.session.add(order)
        flash('Shipped order %s' % order_id)
    elif state == Constants.ORDER_STATUS_DELIVERED:
        order.deliver()
        db.session.add(order)
        flash('Delivered order %s' % order_id)
    elif state == Constants.ORDER_ACTION_NOTIFY:
        order.notify()
        db.session.add(order)
        db.session.commit()
        return redirect(url_for('client.review_notification', order_id=order.id))
    elif state == Constants.ORDER_ACTION_CANCEL_REVIEW:
        order.cancel_review()
        db.session.add(order)
        flash('Canceled review on order %s' % order_id)
    if state == Constants.ORDER_ACTION_DELETE:
        db.session.delete(order)
        flash('Deleted order %s' % order_id)
    if not failure:
        db.session.commit()
        return redirect(url_for('client.shop_dashboard'))
    flash('Invalid state %s' % state)
    return redirect(url_for('client.shop_dashboard'))


@client.route('/review-notification', defaults={'order_id': None})
@client.route('/review-notification/<int:order_id>')
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def review_notification(order_id):
    shops = Shop.query.filter_by(owner_id=current_user.id).all()
    order = Order.query.filter_by(id=order_id).first()
    if order.shop_id not in [s.id for s in shops]:
        flash('Not your shop')
        return redirect('client.dashboard')
    return render_template('shop_admin/send_notification.html', review_requests=order.review_requests)


@client.route('/send-notification', defaults={'review_request_id': None})
@client.route('/send-notification/<int:review_request_id>', methods=["POST"])
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def send_notification(review_request_id):
    shops = Shop.query.filter_by(owner_id=current_user.id).all()
    review_request = ReviewRequest.query.filter_by(id=review_request_id).first()
    if not review_request:
        return redirect('client.shop_dashboard')
    if review_request.for_product.shop.id not in [s.id for s in shops]:
        flash('Not your shop')
        return redirect('client.shop_dashboard')
    post = get_post_payload()
    recipients = [review_request.to_user.email]
    template = 'email/review_order.html'
    template_ctx = {'review_request': review_request}
    subject = post.get('subject')
    from async import tasks

    tasks.send_email.delay(recipients=recipients,
                           template=template,
                           template_ctx=template_ctx,
                           subject=subject)
    flash('email to %s sent' % recipients)
    return redirect(url_for('client.shop_dashboard'))
