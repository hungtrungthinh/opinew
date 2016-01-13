import datetime
import os
from werkzeug.datastructures import MultiDict
from flask import request, redirect, url_for, render_template, flash, g, send_from_directory, \
    current_app, make_response, abort, jsonify
from flask.ext.security import login_required, login_user, current_user, roles_required, logout_user
from providers.shopify_api import API
from webapp import db
from webapp.client import client
from webapp.models import Review, Shop, Platform, User, Product, Order, Notification, ReviewRequest, Plan, Question, \
    Task, UserLegacy
from webapp.common import param_required, catch_exceptions, get_post_payload
from webapp.exceptions import ParamException, DbException, ApiException
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
        # check that the access token is still valid
        shopify_api = API(shop_domain=shop_domain, access_token=shop.access_token)
        try:
            webhooks_count = shopify_api.check_webhooks_count()
            # okay, the token is still valid!
            if not webhooks_count == Constants.EXPECTED_WEBHOOKS:
                raise DbException('invalid count of webhooks')
            return redirect(url_for('client.shop_dashboard'))
        except (ApiException, DbException) as e:
            # The token is no longer valid, delete
            shop.access_token = None
            db.session.add(shop)
            db.session.commit()

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

    # Create db records
    # Create shop user, generate pass
    shop_owner_email = shopify_shop.get('email', '')
    shop_owner_name = shopify_shop.get('shop_owner', '')
    shop_owner, is_new = User.get_or_create_by_email(shop_owner_email,
                                                     role_name=Constants.SHOP_OWNER_ROLE,
                                                     name=shop_owner_name)
    if is_new:
        db.session.add(shop_owner)
        db.session.commit()
    shop_owner_id = shop_owner.id

    # Create shop with owner = shop_user
    shopify_platform = Platform.get_by_name('shopify')
    shop = Shop(name=shop_name,
                domain=shop_domain,
                platform=shopify_platform,
                access_token=shopify_api.access_token,
                owner=shop_owner)
    shop_owner.shops.append(shop)
    db.session.add(shop)
    db.session.commit()

    # asyncronously create all products, orders and webhooks
    from async import tasks

    args = dict(shopify_api=shopify_api, shop_id=shop.id)
    task = Task.create(method=tasks.create_shopify_shop, args=args)
    db.session.add(task)
    db.session.commit()

    # Login shop_user
    shop_owner = User.query.filter_by(id=shop_owner_id).first()
    login_user(shop_owner)
    return redirect(url_for('client.shop_dashboard', first='1'))

# Signals
from flask.ext.security import user_registered

user_registered.connect(User.post_registration_handler)


@client.route('/')
def index():
    if 'mobile' in g and g.mobile:
        if current_user.is_authenticated():
            if current_user.has_role(Constants.REVIEWER_ROLE):
                return redirect(url_for('client.user_profile', user_id=current_user.id))
        else:
            return redirect(url_for('client.reviews'))

    if current_user.is_authenticated():
        if current_user.temp_password:
            return redirect('/change')
        if current_user.has_role(Constants.ADMIN_ROLE):
            return redirect('/admin')
        elif current_user.has_role(Constants.SHOP_OWNER_ROLE):
            return redirect(url_for('client.shop_dashboard'))
        elif current_user.has_role(Constants.REVIEWER_ROLE):
            return redirect(url_for('client.user_profile', user_id=current_user.id))
    return render_template('index.html')


@client.route('/', defaults={'review_request_token': ''})
@client.route('/<path:review_request_token>')
def get_by_review_request_token(review_request_token):
    review_request = ReviewRequest.query.filter_by(token=review_request_token).first()
    user_email = None
    is_legacy = False
    # all below logic is to decide whether to display the Name, Email and Password fields
    if review_request:
        if review_request.to_user:
            if current_user.is_authenticated() and current_user.id != review_request.to_user.id:
                logout_user()  # logout the current user who is different to the one who got the email
                user_email = review_request.to_user.email  # set the email to the user that got the email.
            elif current_user.is_authenticated() and current_user.id == review_request.to_user.id:
                pass  # we don't need to do anything. current user is logged in
            elif not current_user.is_authenticated():
                user_email = review_request.to_user.email
        elif review_request.to_user_legacy:
            is_legacy = True
            user_email = review_request.to_user_legacy.email  # set the email to the user that got the email.
            if current_user.is_authenticated():
                logout_user()

        return redirect(url_for('client.add_review', review_request_id=review_request.id,
                                review_request_token=review_request.token,
                                user_email=user_email, is_legacy=is_legacy, **request.args))
    return redirect(url_for('client.index'), code=301)


@client.route('/reviews')
def reviews():
    if 'mobile' in g and g.mobile:
        page = request.args.get('page', '1')
        page = int(page) if page.isdigit() else 1
        start = Constants.REVIEWS_PER_PAGE * (page - 1)
        end = start + Constants.REVIEWS_PER_PAGE
        reviews = Review.get_latest(start, end)
        return render_template('reviews.html',
                               page_title="Reviews - Opinew",
                               page_description="Featured product reviews with images, videos, emojis, gifs and memes.",
                               reviews=reviews, page=page)
    page = request.args.get('page', '1')
    page = int(page) if page.isdigit() else 1
    start = Constants.REVIEWS_PER_PAGE * (page - 1)
    end = start + Constants.REVIEWS_PER_PAGE
    reviews = Review.get_latest(start, end)
    return render_template('reviews.html',
                           page_title="Reviews - Opinew",
                           page_description="Featured product reviews with images, videos, emojis, gifs and memes.",
                           reviews=reviews, page=page)


@client.route('/settings')
def settings():
    if 'mobile' in g and g.mobile:
        return render_template('mobile/settings.html')
    return redirect(url_for('client.index'))


@client.route('/notifications')
def notifications():
    if 'mobile' in g and g.mobile:
        return render_template('mobile/notifications.html')
    return redirect(url_for('client.index'))


@client.route('/user-profile', defaults={'user_id': 0})
@client.route('/user-profile/<int:user_id>')
def user_profile(user_id):
    if 'mobile' in g and g.mobile:
        page = 1
        user = User.get_by_id(user_id)
        reviews = Review.get_by_user(user_id)
        return render_template('mobile/user_profile.html',
                               page_title="User - Opinew",
                               reviews=reviews, page=page, user=user)
    page = 1
    user = User.get_by_id(user_id)
    reviews = Review.get_by_user(user_id)
    return render_template('mobile/user_profile.html',
                           page_title="User - Opinew",
                           reviews=reviews, page=page, user=user)


@client.route('/dashboard')
@login_required
@roles_required(Constants.SHOP_OWNER_ROLE)
def shop_dashboard():
    shop_form, platforms = None, None
    shops = current_user.shops
    if not shops:
        shop_form = ShopForm()
        platforms = Platform.query.all()
    if len(shops) == 1:
        return redirect(url_for('client.shop_dashboard_id', shop_id=shops[0].id, **request.args))
    return render_template('shop_admin/choose_shop.html', shops=shops, shop_form=shop_form, platforms=platforms)


@client.route('/dashboard', defaults={'shop_id': 0})
@client.route('/dashboard/<int:shop_id>')
@login_required
@roles_required(Constants.SHOP_OWNER_ROLE)
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
    plans = Plan.query.all()
    expiry_days = (
    current_user.confirmed_at + datetime.timedelta(days=Constants.TRIAL_PERIOD_DAYS) - datetime.datetime.utcnow()).days
    return render_template('shop_admin/home.html', shop=shop, code=code, shop_form=shop_form,
                           review_request_form=review_request_form, platforms=platforms,
                           plans=plans, expiry_days=expiry_days)


@client.route('/dashboard', defaults={'shop_id': 0})
@client.route('/dashboard/<int:shop_id>/orders')
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def shop_dashboard_orders(shop_id):
    now = datetime.datetime.utcnow()
    shop = Shop.query.filter_by(owner_id=current_user.id, id=shop_id).first()
    if not shop:
        flash('Not your shop')
        return redirect(url_for('client.shop_dashboard'))
    orders = Order.query.filter_by(shop_id=shop_id).order_by(Order.purchase_timestamp.desc()).all()
    return render_template("shop_admin/orders.html", orders=orders, now=now)


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


@client.route('/dashboard', defaults={'shop_id': 0})
@client.route('/dashboard/<int:shop_id>/questions')
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def shop_dashboard_questions(shop_id):
    shop = Shop.query.filter_by(owner_id=current_user.id, id=shop_id).first()
    if not shop:
        flash('Not your shop')
        return redirect(url_for('client.shop_dashboard'))
    products = Product.query.filter_by(shop_id=shop_id).all()
    questions = Question.query.filter(Question.about_product_id.in_([p.id for p in products])).all()
    return render_template("shop_admin/questions.html", questions=questions)


@client.route('/dashboard', defaults={'shop_id': 0})
@client.route('/dashboard/<int:shop_id>/tasks')
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def shop_dashboard_tasks(shop_id):
    shop = Shop.query.filter_by(owner_id=current_user.id, id=shop_id).first()
    if not shop:
        flash('Not your shop')
        return redirect(url_for('client.shop_dashboard'))
    orders = Order.query.filter_by(shop=shop).all()
    orders_with_tasks = [order for order in orders if order.task_id]
    return render_template("shop_admin/tasks.html", orders_with_tasks=orders_with_tasks)


@client.route('/add-payment-card', methods=['POST'])
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def add_payment_card():
    stripe_token = request.form.get('stripe-token')
    customer = current_user.customer[0]
    customer.add_payment_card(stripe_token)
    db.session.add(customer)
    db.session.commit()
    flash("Card added successfully!")
    return redirect(request.referrer)


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
            return '', 404
        shop = product.shop
        if shop.owner and \
                shop.owner.customer and \
                shop.owner.customer[0] and \
                        (datetime.datetime.utcnow() - shop.owner.confirmed_at).days > Constants.TRIAL_PERIOD_DAYS and \
                not shop.owner.customer[0].last4:
            return '', 404

        if current_user and current_user.is_authenticated():
            own_review = Review.query.filter_by(product_id=product.id, user=current_user).order_by(Review.created_ts.desc()).first()
        else:
            own_review = None
        all_reviews = Review.query.filter_by(product_id=product.id, approved_by_shop=True).order_by(Review.created_ts.desc()).all()
        featured_reviews = [fr for fr in all_reviews if fr.featured and fr.featured.action == 1 and not fr == own_review]
        rest_reviews = [r for r in all_reviews if r not in featured_reviews and not r == own_review]
        next_arg = request.url
        product.plugin_views += 1
        db.session.commit()
    except (ParamException, DbException, AssertionError, AttributeError) as e:
        return '', 404
    return render_template('plugin/plugin.html', product=product, rest_reviews=rest_reviews,
                           signup_form=signup_form, login_form=login_form, review_form=review_form,
                           review_image_form=review_image_form, next_arg=next_arg,
                           own_review=own_review, featured_reviews=featured_reviews, in_plugin=True)


@client.route('/product', defaults={'product_id': 0})
@client.route('/product/<int:product_id>')
def get_product(product_id):
    try:
        product = Product.get_by_id(product_id)
        if current_user and current_user.is_authenticated():
            own_review = Review.query.filter_by(product_id=product_id, user=current_user).order_by(
                Review.created_ts.desc()).first()
        else:
            own_review = None
        reviews = Review.query.filter_by(product_id=product_id).order_by(Review.created_ts.desc()).all()
        featured_reviews = [fr for fr in reviews if fr.featured and fr.featured.action == 1 and not fr == own_review]
        reviews = [r for r in reviews if r not in featured_reviews and not r == own_review]
    except (ParamException, DbException) as e:
        flash(e.message)
        return redirect(request.referrer)
    return render_template('product.html', page_title="%s Reviews - " % product.name,
                           product=product,
                           reviews=reviews,
                           own_review=own_review,
                           featured_reviews=featured_reviews)


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
    ctx['show_recaptcha'] = not current_user.is_authenticated()
    if 'review_request_id' in request.args and 'review_request_token' in request.args:
        review_request = ReviewRequest.query.filter_by(id=request.args.get('review_request_id')).first()
        if not review_request or not review_request.token == request.args.get('review_request_token'):
            flash('Incorrect review request token')
            ctx['show_recaptcha'] = True
        else:
            ctx['show_recaptcha'] = False
            ctx['product'] = review_request.for_product
            if review_request.to_user and review_request.to_user.name:
                ctx['user_name'] = review_request.to_user.name.split()[0]
                ctx['is_legacy'] = False
            elif review_request.to_user_legacy and review_request.to_user_legacy.name:
                ctx['user_name'] = review_request.to_user_legacy.name.split()[0]
                ctx['is_legacy'] = True
    if 'user_email' in request.args:
        ctx['user_email'] = request.args.get('user_email')
    # TODO what is this line below???
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


@client.route('/render-order-review-email')
def render_order_review_email():
    order_id = request.args.get('order_id')
    if not order_id:
        return 'no order id supplied', 404
    order = Order.query.filter_by(id=order_id).first()
    if not order:
        return 'cant find the order', 404
    shops = Shop.query.filter_by(owner_id=current_user.id).all()
    if order.shop_id not in [s.id for s in shops]:
        flash('Not your shop')
        return redirect(url_for('client.shop_dashboard'))
    template_ctx = order.build_review_email_context()
    return render_template('email/review_order.html', **template_ctx)


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
    if order.shop_id not in [s.id for s in shops]:
        flash('Not your shop')
        return redirect(url_for('client.shop_dashboard'))
    if state == Constants.ORDER_STATUS_SHIPPED:
        if order.status == Constants.ORDER_STATUS_PURCHASED:
            order.ship()
            if not order.review_requests:
                order.create_review_requests(order.id)
        db.session.add(order)
        flash('Shipped order %s' % order_id)
    elif state == Constants.ORDER_ACTION_NOTIFY:
        if not order.review_requests:
            order.create_review_requests(order.id)
        order.cancel_review()
        order.notify()
        db.session.add(order)
        db.session.commit()
        return redirect(url_for('client.review_notification', order_id=order.id))
    elif state == Constants.ORDER_ACTION_CANCEL_REVIEW:
        order.cancel_review()
        db.session.add(order)
        flash('Canceled review on order %s' % order_id)
    elif state == Constants.ORDER_ACTION_DELETE:
        db.session.delete(order)
        flash('Deleted order %s' % order_id)
    else:
        flash('Invalid state %s' % state)

    db.session.commit()
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
    return render_template('shop_admin/send_notification.html', order=order)


@client.route('/send-notification', defaults={'order_id': None})
@client.route('/send-notification/<int:order_id>', methods=["POST"])
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def send_notification(order_id):
    shops = Shop.query.filter_by(owner_id=current_user.id).all()
    order = Order.query.filter_by(id=order_id).first()
    review_request = order.review_requests[0] if order.review_requests else None
    if not review_request:
        flash('No review request connected to this order')
        return redirect('client.shop_dashboard')
    if review_request.for_product.shop.id not in [s.id for s in shops]:
        flash('Not your shop')
        return redirect('client.shop_dashboard')
    post = get_post_payload()
    recipients = []
    if review_request.to_user:
        recipients = [review_request.to_user.email]
    elif review_request.to_user_legacy:
        recipients = [review_request.to_user_legacy.email]
    template = 'email/review_order.html'
    template_ctx = order.build_review_email_context()
    subject = post.get('subject')
    from async import tasks

    args = dict(recipients=recipients,
                template=template,
                template_ctx=template_ctx,
                subject=subject)
    task = Task.create(method=tasks.send_email, args=args)
    db.session.add(task)
    db.session.commit()
    flash('email to %s sent' % recipients[0])
    return redirect(url_for('client.shop_dashboard'))


@client.route('/post-change')
@login_required
def post_change():
    if current_user.is_authenticated() and current_user.temp_password:
        current_user.temp_password = None
        db.session.add(current_user)
        db.session.commit()
    return redirect(url_for('client.index'))


@client.route('/admin-view-as')
@login_required
@roles_required(Constants.ADMIN_ROLE)
def admin_view_as():
    user_id = request.args.get('user_id')
    from webapp import models

    user = models.User.query.filter_by(id=user_id).first()
    if user:
        logout_user()
        login_user(user)
    return redirect(url_for('client.index'))


@client.route('/admin-revoke-task')
@login_required
@roles_required(Constants.ADMIN_ROLE)
def admin_revoke_task():
    task_id = request.args.get('task_id')
    from async import celery_async

    celery_async.revoke_task(task_id)
    task = Task.query.filter_by(celery_uuid=task_id).first()
    if task:
        task.status = 'REVOKED'
        db.session.add(task)
        db.session.commit()
    flash("Removed task %s" % task_id)
    return redirect(url_for('client.index'))
