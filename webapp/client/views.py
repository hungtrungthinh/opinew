from __future__ import division
import datetime
import re
import os
import httplib
import urllib
from functools import wraps
from flask import request, redirect, url_for, render_template, flash, g, send_from_directory, \
    current_app, make_response, abort, jsonify, send_file, Response, session
from flask.ext.security import login_required, login_user, current_user, roles_required, logout_user
from flask_security.utils import verify_password
from providers.shopify_api import API
from webapp import db, review_images, limiter
from webapp.client import client
from webapp.models import Review, Shop, Platform, User, Product, Order, Notification, ReviewRequest, Plan, Question, \
    Task, SentEmail, FunnelStream, Subscription, ProductUrl, UserLegacy, ReviewLike, ReviewReport, ReviewShare, \
    ReviewFeature, UrlReferer, Comment, Answer, NextAction
from webapp.common import param_required, catch_exceptions, get_post_payload
from webapp.exceptions import ParamException, DbException, ApiException, ExceptionMessages, RequirementException
from webapp.forms import LoginForm, ReviewForm, ReviewImageForm, ShopForm, ExtendedRegisterForm
from config import Constants, basedir
from providers import giphy
from webapp.strategies import rank_objects_for_product, get_scheduled_tasks, get_incoming_messages, get_reviews, \
    get_analytics
from messages import SuccessMessages
from werkzeug.routing import BuildError
from assets import strings


def verify_requirements(*redirect_url_for):
    """
    Wraps a response object by verifying that all required conditions pass
    :param f:
    :return:
    """

    def outer_wrapper(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Create a response context - is it asyncrounous call (e.g. from ajax)
            payload = request.args if request.method in ['GET'] else request.form
            is_async = payload.get('async')

            # get as many default redirects as possible
            default_redirects = []
            for redirect_url in redirect_url_for:
                try:
                    default_redirects.append(url_for(redirect_url))
                except BuildError:
                    # well, this url_for was invalid, don't break everything, move on
                    pass

            # decide which exceptions to catch
            if current_app.debug:
                exception_list = (RequirementException, AssertionError)
            else:
                exception_list = (Exception, AssertionError)
            try:
                return f(*args, **kwargs)
            except exception_list as e:
                error_message = e.message or ExceptionMessages.UNKNOWN_ERROR
                error_code = e.error_code if hasattr(e, 'error_code') else httplib.BAD_REQUEST
                error_category = e.error_category if hasattr(e, 'error_category') else Constants.ALERT_ERROR_LABEL

                # If it an async request - then return jsonified response
                if is_async:
                    return jsonify({"error": error_message}), error_code
                flash(error_message, category=error_category)

                # try to avoid 1 level deep infinite loop redirect
                referer_redirect = request.referrer if not request.referrer == request.path else None
                ctx_redirect = None
                for default_redirect in default_redirects:
                    ctx_redirect = default_redirect if not default_redirect == request.path else None
                    if ctx_redirect:
                        break
                # transfer form data to args

                request_args = dict(request.args)
                for k, w in request.form.iteritems():
                    if k in ['password', 'csrf_token']:
                        continue
                    request_args[k] = w
                final_redirect = referer_redirect or ctx_redirect or url_for('client.index')
                # add the args to the final_redirect uri
                query = urllib.urlencode(request_args)
                if '?' in final_redirect:
                    final_redirect = final_redirect.split('?')[0] + '?' + query
                else:
                    final_redirect += '?' + query
                return redirect(final_redirect)

        return wrapper

    return outer_wrapper


def verify_required_condition(condition, error_msg, error_code=httplib.BAD_REQUEST,
                              error_category=Constants.ALERT_ERROR_LABEL):
    """
    Makes sure that the required condition is truthy. Otherwise raises a response error which is either
    jsonified response (if the resource has been required async) or flashing.
    :param condition: the condition
    :param error_msg: the error message to display
    :param error_code: the error code to return
    :return:
    """
    if not condition:
        raise RequirementException(message=error_msg, error_code=error_code, error_category=error_category)


def get_required_parameter(payload, param_name):
    """
    Verifies and returns a parameter from a payload
    :param payload: the payload to check
    :param param_name: the parameter name
    :return:
    """
    obj = payload.get(param_name)
    verify_required_condition(condition=obj,
                              error_msg=ExceptionMessages.MISSING_PARAM.format(param=param_name),
                              error_code=httplib.BAD_REQUEST)
    return obj


def get_required_model_instance_by_id(model, instance_id):
    """
    Verifies and returns a model instance that is identified by id
    :param model: the Model to check
    :param instance_id: the instance id
    :return: a model instance by id
    """
    obj = model.query.filter_by(id=instance_id).first()
    verify_required_condition(condition=obj is not None,
                              error_msg=ExceptionMessages.INSTANCE_NOT_EXISTS.format(instance=model.__name__,
                                                                                     id=instance_id),
                              error_code=httplib.BAD_REQUEST)
    return obj


def generate_success_response_from_obj(obj, obj_name):
    payload = request.args if request.method in ['GET'] else request.form
    is_async = payload.get('async')
    if is_async:
        return jsonify(obj.serialize()), httplib.CREATED
    flash(SuccessMessages.SUCCESS_CREATING_OBJECT.format(object_name=obj_name))
    return redirect(request.referrer)


@client.route('/kitchen-sink')
@roles_required(Constants.ADMIN_ROLE)
@login_required
def kitchen_sink():
    flash('This is dangerous', category=Constants.ALERT_ERROR_LABEL)
    flash('Careful hello!!', category=Constants.ALERT_WARNING_LABEL)
    flash('hello?', category=Constants.ALERT_INFO_LABEL)
    flash('hello okay', category=Constants.ALERT_PRIMARY_LABEL)
    flash('YES hello', category=Constants.ALERT_SUCCESS_LABEL)
    return render_template('dev/kitchen_sink.html')


@client.route('/')
def index():
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


@client.route('/terms')
def terms_of_use():
    return render_template('legal/terms_of_use.html', page_title="Terms of Use - ")


@client.route('/privacy')
def privacy_policy():
    return render_template('legal/privacy_policy.html', page_title="Privacy Policy - ")


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
                                                     name=shop_owner_name,
                                                     plan_name=Constants.PLAN_NAME_SHOPIFY_SIMPLE)
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

    # create next tasks
    # set new next action
    now = datetime.datetime.utcnow()
    im1 = NextAction(
            shop=shop,
            timestamp=now,
            identifier=Constants.NEXT_ACTION_ID_SETUP_YOUR_SHOP,
            title=strings.NEXT_ACTION_SETUP_YOUR_SHOP,
            url=url_for('client.setup_plugin', shop_id=shop.id),
            icon=Constants.NEXT_ACTION_SETUP_YOUR_SHOP_ICON,
            icon_bg_color=Constants.NEXT_ACTION_SETUP_YOUR_SHOP_ICON_BG_COLOR
    )
    db.session.add(im1)

    im2 = NextAction(
            timestamp=now,
            shop=shop,
            identifier=Constants.NEXT_ACTION_ID_SETUP_BILLING,
            title=strings.NEXT_ACTION_SETUP_BILLING,
            url="javascript:showTab('#account');",
            icon=Constants.NEXT_ACTION_SETUP_BILLING_ICON,
            icon_bg_color=Constants.NEXT_ACTION_SETUP_BILLING_ICON_BG_COLOR
    )
    db.session.add(im2)

    im3 = NextAction(
            timestamp=now,
            shop=shop,
            identifier=Constants.NEXT_ACTION_ID_CHANGE_YOUR_PASSWORD,
            title=strings.NEXT_ACTION_CHANGE_YOUR_PASSWORD,
            url=url_for('security.change_password'),
            icon=Constants.NEXT_ACTION_CHANGE_YOUR_PASSWORD_ICON,
            icon_bg_color=Constants.NEXT_ACTION_CHANGE_YOUR_PASSWORD_ICON_BG_COLOR
    )
    db.session.add(im3)

    # Login shop_user
    shop_owner = User.query.filter_by(id=shop_owner_id).first()
    login_user(shop_owner)
    return redirect(url_for('client.setup_plugin', shop_id=shop.id))


# Signals
from flask.ext.security import user_registered

user_registered.connect(User.post_registration_handler)


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
        # update rr opened ts
        review_request.opened_timestamp = datetime.datetime.utcnow()
        db.session.add(review_request)
        db.session.commit()

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
@verify_requirements('client.reviews')
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def shop_dashboard_id(shop_id):
    shop = get_required_model_instance_by_id(Shop, shop_id)
    verify_required_condition(condition=shop.owner_id == current_user.id,
                              error_msg=ExceptionMessages.NOT_YOUR_INSTANCE.format(instance='shop'))
    dashboard_tabs = Constants.DASHBOARD_TABS
    incoming_messages = get_incoming_messages(shop)
    scheduled_tasks = get_scheduled_tasks(shop)
    reviews = get_reviews(shop)
    stats = get_analytics(shop)
    return render_template('dashboard/dashboard.html',
                           shop=shop,
                           dashboard_tabs=dashboard_tabs,
                           incoming_messages=incoming_messages,
                           scheduled_tasks=scheduled_tasks,
                           reviews=reviews,
                           stats=stats)


@client.route('/setup-plugin/<int:shop_id>')
@verify_requirements('client.dashboard')
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def setup_plugin(shop_id):
    shop = get_required_model_instance_by_id(Shop, shop_id)
    # TODO: import product url
    product_page_url = shop.products[0].url if shop.products else None
    return render_template('user_setup/shopify.html',
                           product_page_url=product_page_url,
                           shop=shop)


@client.route('/change-subscription', methods=['POST'])
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def change_subscription():
    shop_id = request.form.get('shop_id')
    if not shop_id:
        flash('Shop_id required')
        return redirect(url_for('client.shop_dashboard'))
    shop = Shop.query.filter_by(owner_id=current_user.id, id=shop_id).first()
    if not shop:
        flash('Not your shop')
        return redirect(url_for('client.shop_dashboard'))
    plan_id = request.form.get('plan_id')
    if not plan_id:
        flash('Plan_id required')
        return redirect(url_for('client.shop_dashboard'))
    plan = Plan.query.filter_by(id=plan_id).first()
    if not plan:
        flash('Plan does not exist')
        return redirect(url_for('client.shop_dashboard'))
    subscription = current_user.customer[0].subscription[0]
    if not subscription:
        flash('Subscription does not exist')
        return redirect(url_for('client.shop_dashboard'))
    subscription = Subscription.update(subscription, plan)
    db.session.add(subscription)
    db.session.commit()
    flash('Subscription changed successfully')
    return redirect(request.referrer or url_for('client.shop_dashboard'))


@client.route('/dashboard', defaults={'shop_id': 0})
@client.route('/dashboard/<int:shop_id>/orders')
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def shop_dashboard_orders(shop_id):
    start = int(request.args.get('start', 0))
    end = start + Constants.DASHBOARD_ORDERS_LIMIT
    if start and not end > start > 0:
        return ''
    now = datetime.datetime.utcnow()
    shop = Shop.query.filter_by(owner_id=current_user.id, id=shop_id).first()
    if not shop:
        flash('Not your shop')
        return redirect(url_for('client.shop_dashboard'))
    orders = Order.query.filter_by(shop_id=shop_id).order_by(Order.purchase_timestamp.desc()).all()[start:end]
    return render_template("shop_admin/orders.html", orders=orders, now=now)


@client.route('/add-product', methods=['POST'])
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def add_product():
    shop_id = request.form.get('shop_id')
    if not shop_id:
        flash('Shop_id required')
        return redirect(url_for('client.shop_dashboard'))
    shop = Shop.query.filter_by(owner_id=current_user.id, id=shop_id).first()
    if not shop:
        flash('Not your shop')
        return redirect(url_for('client.shop_dashboard'))
    name = request.form.get('name')
    url = request.form.get('url')
    short_description = request.form.get('short_description')
    product = Product(shop=shop, name=name, short_description=short_description)
    product_url = ProductUrl(url=url, is_regex=False)
    product_url.product = product
    db.session.add(product)
    db.session.add(product_url)
    db.session.commit()
    return redirect(request.referrer or url_for('client.shop_dashboard'))


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
    questions = Question.query.filter(Question.product_id.in_([p.id for p in products])).all()
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


@client.route('/get-next-funnel-stream')
def get_next_funnel_stream():
    funnel_stream = FunnelStream()
    db.session.add(funnel_stream)
    db.session.commit()
    funnel_stream_id = funnel_stream.id
    resp = Response("%s" % funnel_stream_id)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


@client.route('/plugin')
def get_plugin():
    show_recaptcha = not current_user.is_authenticated()
    try:
        review_form = ReviewForm()
        review_image_form = ReviewImageForm()
        signup_form = ExtendedRegisterForm()
        login_form = LoginForm()
        shop_id = param_required('shop_id', request.args)
        if not shop_id:
            return '', 404
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
                shop.owner.confirmed_at and \
                        (datetime.datetime.utcnow() - shop.owner.confirmed_at).days > Constants.TRIAL_PERIOD_DAYS and \
                not shop.owner.customer[0].last4:
            return '', 404

        product_objs = rank_objects_for_product(product.id)
        next_arg = request.url
        # TODO: deprecate plugin_views
        product.plugin_views += 1
        funnel_stream_id = request.args.get('funnel_stream_id')
        if funnel_stream_id:
            funnel_stream = FunnelStream.query.filter_by(id=funnel_stream_id).first()
            if funnel_stream:
                funnel_stream.shop = shop
                funnel_stream.product = product
                funnel_stream.plugin_load_ts = datetime.datetime.utcnow()
                funnel_stream.plugin_loaded_from_ip = request.remote_addr
                db.session.add(funnel_stream)
                db.session.commit()
    except (ParamException, DbException, AssertionError, AttributeError) as e:
        return '', 404
    return render_template('plugin/plugin.html',
                           product=product,
                           product_objs=product_objs,
                           signup_form=signup_form,
                           login_form=login_form,
                           review_form=review_form,
                           review_image_form=review_image_form,
                           next_arg=next_arg,
                           in_plugin=True,
                           funnel_stream_id=funnel_stream_id,
                           show_recaptcha=show_recaptcha)


@client.route('/plugin-stars')
def get_plugin_stars():
    try:
        shop_id = param_required('shop_id', request.args)
        if not shop_id:
            return '', 404
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
        all_reviews = Review.query.filter_by(product_id=product.id, deleted=False).order_by(
                Review.created_ts.desc()).all()
        stars_list = [r.star_rating for r in all_reviews if r.star_rating]
        average_stars = sum(stars_list) / len(stars_list) if len(stars_list) else 0
    except (ParamException, DbException, AssertionError, AttributeError) as e:
        return '', 404
    return render_template('plugin/plugin_stars.html',
                           product=product,
                           average_stars=average_stars,
                           all_reviews=all_reviews)


@client.route('/update-funnel')
def update_funnel():
    funnel_stream_id = request.args.get('funnel_stream_id')
    if not (funnel_stream_id and funnel_stream_id.isdigit()):
        return jsonify({"message": "funnel_stream_id parameter required"}), 400
    funnel_stream = FunnelStream.query.filter_by(id=funnel_stream_id).first()
    if not funnel_stream:
        return jsonify({"message": "funnel_stream with this id does not exist"}), 400
    action = request.args.get('action')
    if not (action and action in Constants.FUNNEL_STREAM_ACTIONS):
        return jsonify({"message": "action values are %s" % Constants.FUNNEL_STREAM_ACTIONS}), 400
    # disambiguate the action
    if action == 'glimpse':
        funnel_stream.plugin_glimpsed_ts = datetime.datetime.utcnow()
    elif action == 'fully_seen':
        funnel_stream.plugin_fully_seen_ts = datetime.datetime.utcnow()
    elif action == 'mouse_hover':
        funnel_stream.plugin_mouse_hover_ts = datetime.datetime.utcnow()
    elif action == 'mouse_scroll':
        funnel_stream.plugin_mouse_scroll_ts = datetime.datetime.utcnow()
    elif action == 'mouse_click':
        funnel_stream.plugin_mouse_click_ts = datetime.datetime.utcnow()
    db.session.add(funnel_stream)
    db.session.commit()
    resp = Response("")
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


@client.route('/product', defaults={'product_id': 0})
@client.route('/product/<int:product_id>')
def get_product(product_id):
    try:
        product = Product.get_by_id(product_id)
        product_objs = rank_objects_for_product(product_id)
    except (ParamException, DbException) as e:
        flash(e.message)
        return redirect(request.referrer)
    return render_template('product.html',
                           product_objs=product_objs,
                           page_image=product.image_url,
                           page_title="%s Reviews - Opinew" % product.name,
                           product=product)


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
        product_id = request.args.get('product_id')
        ctx['product'] = Product.query.filter_by(id=product_id).first()
        if current_user and current_user.is_authenticated():
            # Check if review by this user exists for this product
            existing_review = Review.query.filter_by(product_id=product_id, user_id=current_user.id).first()
            if existing_review:
                return redirect(url_for('client.edit_review', review_id=existing_review.id))
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
    # If we don't have any product, display a list of all products
    if 'product' not in ctx or not ctx['product']:
        ctx['products'] = Product.query.all()
    # Initialize forms
    ctx['review_image_form'] = ReviewImageForm()
    ctx['review_form'] = ReviewForm()
    return render_template('add_review.html', **ctx)


@client.route('/edit-review', defaults={'review_id': 0})
@client.route('/edit-review/<int:review_id>')
@login_required
def edit_review(review_id):
    review = Review.query.filter_by(id=review_id).first()
    if not review:
        flash(ExceptionMessages.INSTANCE_NOT_EXISTS.format(instance="review", id=review_id))
        return redirect(request.referrer or url_for('client.index'))
    if not review.user == current_user:
        flash(ExceptionMessages.NOT_YOUR_REVIEW)
        return redirect(request.referrer or url_for('client.index'))
    ctx = {}
    ctx['review'] = review
    if review.product_id:
        ctx['product'] = Product.query.filter_by(id=review.product_id).first()
    ctx['review_image_form'] = ReviewImageForm()
    ctx['review_form'] = ReviewForm()
    return render_template('add_review.html', **ctx)


@client.route('/delete-review', defaults={'review_id': 0})
@client.route('/delete-review/<int:review_id>')
@login_required
def delete_review(review_id):
    review = Review.query.filter_by(id=review_id).first()
    if not review:
        flash(ExceptionMessages.INSTANCE_NOT_EXISTS.format(instance="review", id=review_id))
        return redirect(request.referrer or url_for('client.index'))
    if not review.user == current_user:
        flash(ExceptionMessages.NOT_YOUR_REVIEW)
        return redirect(request.referrer or url_for('client.index'))
    review.deleted = True
    review.deleted_ts = datetime.datetime.utcnow()
    db.session.add(review)
    db.session.commit()
    return redirect(
            request.referrer or url_for('client.get_product', product_id=review.product_id) or url_for('client.index'))


@client.route('/reviews', defaults={'review_id': 0})
@client.route('/reviews/<int:review_id>')
def view_review(review_id):
    review = Review.query.filter_by(id=review_id).first()
    if not review:
        flash(ExceptionMessages.INSTANCE_NOT_EXISTS.format(instance='review', id=review_id))
        return redirect(request.referrer or url_for('client.index'))
    return render_template('shop_admin/view_review.html',
                           review=review,
                           page_title='Review by %s about %s' % (review.user_name, review.product.name),
                           page_description=review.body,
                           page_image=review.image_url)


@client.route('/plugin-logout')
@login_required
def plugin_logout():
    logout_user()
    return redirect(request.referrer)


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


@client.route('/opinew-simple')
def render_simple_promo_page():
    return render_template('simple_promotional_page.html')


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


@client.route('/render-marketing-email')
def render_marketing_email():
    return render_template('email/shop_marketing_opinew_simple.html')


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
    should_send = False
    if review_request.to_user:
        recipients = [review_request.to_user.email]
        if not review_request.to_user.unsubscribed:
            should_send = True
    elif review_request.to_user_legacy:
        recipients = [review_request.to_user_legacy.email]
        if not review_request.to_user_legacy.unsubscribed:
            should_send = True
    # even if we don't send, let's create a task so that we log things
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
    if should_send:
        flash('email to %s sent' % recipients[0])
    else:
        flash('Unfortunately, %s has unsubscribed, so we can\'t send email. Sorry!' % recipients[0])
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


@client.route('/welcome')
def welcome():
    if 'email' in request.args and 'password' in request.args:
        user = User.query.filter_by(email=request.args['email']).first()
        if not user:
            return redirect('/login')
        if verify_password(request.args['password'], user.password):
            login_user(user)
            return redirect('/change')
    return redirect('/login')


@client.route('/tracking_pixel')
def tracking_pixel():
    tracking_pixel_id = request.args.get('id')
    sent_email = SentEmail.query.filter_by(tracking_pixel_id=tracking_pixel_id).first()
    if sent_email:
        sent_email.opened_timestamp = datetime.datetime.utcnow()
        db.session.add(sent_email)
        db.session.commit()
    return send_file('static/img/tp.png', mimetype='image/png')


@client.route('/unsubscribe')
def unsubscribe():
    email = request.args.get('email')
    unsubscribe_token = request.args.get('unsubscribe_token')
    if not (email and unsubscribe_token):
        return jsonify({"error": "email and unsubscribe_token are required as params"}), 400
    user = User.query.filter_by(email=email).first()
    if not user:
        user = UserLegacy.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "user does not exist"}), 400
    if not user.unsubscribe_token == unsubscribe_token:
        return jsonify({"error": "unsubscribe tokens do not match"}), 400
    user.unsubscribed = True
    db.session.add(user)
    db.session.commit()
    return "%s has been successfully unsubscribed." % email


@client.route('/ref')
@verify_requirements
def add_referer():
    # Verify required objects
    url = get_required_parameter(request.form, 'url')
    q = get_required_parameter(request.form, 'q')

    # Create UrlReferrer object
    now = datetime.datetime.utcnow()
    ref = UrlReferer(url=url, q=q, timestamp=now)
    if current_user.is_authenticated():
        ref.user = current_user
    db.session.add(ref)
    db.session.commit()
    if url.startswith('http://') or url.startswith('https://'):
        return redirect(url)
    return redirect('http://' + url)


#######################
# OPINEW API DEFINITION
#######################
# GET  /resources                               -> get all resources
# GET  /resources/<id>                          -> get resource by id
# GET  /resources/<id>/act                      -> execute idempotent action on single resource (e.g. search)
# POST /resources/<id>/act                      -> execute action on single resource (e.g. create, like)

# GET  /resources/<id>/sub_resources            -> get sub_resources for resource_id
# GET  /resources/<id>/sub_resources/act        -> execute idempotent action on single sub_resource of resource
# POST /resources/<id>/sub_resources/act        -> execute action on single sub_resource of resource

def get_real_or_anonymous_user():
    """
    Gets the currently saved user - either anonymous or authenticated.
    If no user is authenticated, create one with the next id and store
    it in the session.
    :return:
    """
    if current_user and current_user.is_authenticated():
        return current_user
    # validate that the session cookie is sent - this protects against
    # empty session attacks
    assert not session.new
    # try to get the user_id from the session
    user_id = session.get('anonymous_user_id')
    if user_id:
        user = User.query.filter_by(id=int(user_id)).first()
        if user:
            return user
    user = User()
    db.session.add(user)
    db.session.commit()
    session['anonymous_user_id'] = user.id
    return user


def upgrade_to_real_user(user):
    user.is_legacy = False
    # TODO: Generate password, send email to say 'hi'
    db.session.add(user)
    db.session.commit()


def check_legacy_user(user):
    if user.is_legacy:
        # The user has been imported before from an order
        upgrade_to_real_user(user)
    else:
        password = get_required_parameter(request.form, 'password')
        # try to login user if password is correct
        verify_required_condition(condition=verify_password(password, user.password),
                                  error_msg=ExceptionMessages.WRONG_PASSWORD,
                                  error_code=httplib.UNAUTHORIZED)
        login_user(user)


def validate_or_create_user(user):
    name = get_required_parameter(request.form, 'name')
    email = get_required_parameter(request.form, 'email')
    # Check if that user already exists with this email:
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        # The user already exists somehow
        check_legacy_user(existing_user)
    elif not user.email:
        # The user is completely anonymous, and it doesn't exist in
        # our records - add details and create him officially
        user.name = name
        user.email = email
        upgrade_to_real_user(user)


def score_review(review_id):
    # TODO: Move to async
    # TODO: score this review's body contents for readibility, swear words etc.
    review = get_required_model_instance_by_id(Review, review_id)
    if 'fuck' in review.body:
        review.offensive = 1.0
    db.session.add(review)
    db.session.commit()


def verify_review_request(review):
    review_request_id = request.form.get('review_request_id')
    if review_request_id:
        review_request_token = get_required_parameter(request.form, 'review_request_token')
        review_request = get_required_model_instance_by_id(ReviewRequest, review_request_id)
        verify_required_condition(condition=review_request.token == review_request_token)
        verify_required_condition(condition=review_request.to_user == review.user)
        verify_required_condition(condition=review_request.for_product == review.product)
        review.verified_review = True


def schedule_scoring_of_review(review_id):
    # TODO: Create a task for scoring a review
    pass


def create_default_body_from_stars(review):
    if not review.body:
        if review.star_rating:
            review.body = Constants.DEFAULT_BODY_STARS.format(star_rating=review.star_rating)
        else:
            review.body = ""


def is_review_by_shop_owner(review):
    product = review.product
    if product and product.shop and product.shop.owner and product.shop.owner == current_user:
        review.by_shop_owner = True


def review_has_youtube(review):
    if review.body and (Constants.YOUTUBE_WATCH_LINK in review.body or Constants.YOUTUBE_SHORT_LINK in review.body):
        # we have youtube video somewhere in the body, let's extract it
        if Constants.YOUTUBE_WATCH_LINK in review.body:
            youtube_link = Constants.YOUTUBE_WATCH_LINK
        else:
            youtube_link = Constants.YOUTUBE_SHORT_LINK
        # find the youtube video id
        youtube_video_id = review.body.split(youtube_link)[1].split(' ')[0].split('?')[0].split('&')[0]
        review.youtube_video = Constants.YOUTUBE_EMBED_URL.format(youtube_video_id=youtube_video_id)
        # Finally, remove the link from the body
        to_remove = youtube_link + review.body.split(youtube_link)[1].split(' ')[0]
        review.body = re.sub(r"\s*" + re.escape(to_remove) + r"\s*", '', review.body)


def create_review(product, user, body, star_rating, image_url):
    now = datetime.datetime.utcnow()
    review = Review(product=product,
                    user=user,
                    body=body,
                    star_rating=star_rating,
                    image_url=image_url,
                    created_ts=now)

    # Is this a verified review?
    verify_review_request(review)
    create_default_body_from_stars(review)
    is_review_by_shop_owner(review)
    review_has_youtube(review)

    # All checks pass, commit now
    db.session.add(review)
    db.session.commit()

    # Start a pipeline to score the review's various characteristics
    schedule_scoring_of_review(review.id)
    return review


@client.route('/blank_not_found')
def route_blank_not_found():
    return '', 404


@client.route('/no_redirect')
def no_redirect():
    return render_template("no_redirect.html")


@client.route('/simple')
def route_simple_index():
    review = Review.query.first()
    return render_template('simple_index.html', review=review)


@client.route('/plugins/product')
@verify_requirements('client.blank_not_found')
def route_plugin_product():
    get_by = get_required_parameter(request.args, 'get_by')
    if get_by == 'url':
        shop_id = get_required_parameter(request.args, 'shop_id')
        product_url = get_required_parameter(request.args, 'product_url')
        product = Product.find_product_by_url(product_url, shop_id)
    elif get_by == 'platform_id':
        platform_product_id = param_required('platform_product_id', request.args)
        product = Product.query.filter_by( platform_product_id=platform_product_id).first()
    product_objs = rank_objects_for_product(product.id)
    review_form = ReviewForm(request.args)
    return render_template('simple/product_plugin.html',
                           product=product,
                           product_objs=product_objs,
                           review_form=review_form)


@client.route('/reviews/<int:review_id>/like', methods=['POST'])
@verify_requirements('client.reviews')
def route_review_like(review_id):
    review = get_required_model_instance_by_id(Review, review_id)
    user = get_real_or_anonymous_user()
    # verify that this user hasn't liked it before
    review_like = ReviewLike.query.filter_by(review_id=review_id, user_id=user.id).first()
    if not review_like:
        now = datetime.datetime.utcnow()
        new_action = True
        review_like = ReviewLike(review_id=review_id, user_id=user.id, timestamp=now)
        db.session.add(review_like)
    else:
        new_action = False
        db.session.delete(review_like)
    db.session.commit()
    if request.args.get('async'):
        return jsonify({
            'action': new_action,
            'count': len(review.likes)
        })
    return redirect(request.referrer or url_for('client.reviews'))


@client.route('/reviews/<int:review_id>/report', methods=['POST'])
@verify_requirements('client.reviews')
def route_review_report(review_id):
    review = get_required_model_instance_by_id(Review, review_id)
    user = get_real_or_anonymous_user()
    review_report = ReviewReport.query.filter_by(review_id=review_id, user_id=user.id).first()
    if not review_report:
        now = datetime.datetime.utcnow()
        new_action = True
        review_report = ReviewReport(review_id=review_id, user_id=user.id, timestamp=now)
        db.session.add(review_report)
    else:
        new_action = False
        db.session.delete(review_report)
    db.session.commit()
    if request.args.get('async'):
        return jsonify({
            'action': new_action,
            'count': len(review.reports)
        })
    return redirect(request.referrer or url_for('client.reviews'))


@client.route('/reviews/<int:review_id>/feature', methods=['POST'])
@roles_required(Constants.SHOP_OWNER_ROLE)
@login_required
def route_review_feature(review_id):
    review = get_required_model_instance_by_id(Review, review_id)
    verify_required_condition(condition=review.product and review.product.shop and review.product.shop not in current_user.shops,
                              error_msg=ExceptionMessages.CANT_FEATURE_THAT_REVIEW)
    review_feature = ReviewFeature.query.filter_by(review_id=review_id).first()
    if not review_feature:
        now = datetime.datetime.utcnow()
        new_action = True
        review_feature = ReviewFeature(review_id=review_id, user_id=current_user.id, timestamp=now)
        db.session.add(review_feature)
    else:
        new_action = False
        db.session.delete(review_feature)
    db.session.commit()
    if request.args.get('async'):
        return jsonify({
            'action': new_action,
            'count': 1 if review.featured else 0
        })
    return redirect(request.referrer or url_for('client.reviews'))


@client.route('/reviews/<int:review_id>/share', methods=['POST'])
@verify_requirements('client.reviews')
def route_review_share(review_id):
    # Verify required objects
    review = get_required_model_instance_by_id(Review, review_id)

    # Create Review Share
    now = datetime.datetime.utcnow()
    review_share = ReviewShare(timestamp=now, review=review)
    if current_user.is_authenticated():
        review_share.user = current_user
    db.session.add(review_share)
    db.session.commit()

    return generate_success_response_from_obj(obj=review_share, obj_name='Review Share')


@client.route('/reviews/<int:review_id>/comments/create', methods=['POST'])
@verify_requirements('client.reviews')
@login_required
def route_review_comment_create(review_id):
    # Verify required objects
    body = get_required_parameter(request.form, 'body')
    review = get_required_model_instance_by_id(Review, review_id)

    # Create Comment
    now = datetime.datetime.utcnow()
    comment = Comment(user=current_user,
                      body=body,
                      review=review,
                      created_ts=now)
    db.session.add(comment)
    db.session.commit()
    return generate_success_response_from_obj(obj=comment, obj_name='comment')


@client.route('/products/<int:product_id>/questions/create', methods=['POST'])
@verify_requirements('client.reviews')
@login_required
def route_product_question_create(product_id):
    # Verify required objects
    product_id = get_required_parameter(request.form, 'product_id')
    body = get_required_parameter(request.form, 'body')
    product = get_required_model_instance_by_id(Product, product_id)

    # Create Question
    now = datetime.datetime.utcnow()
    question = Question(user=current_user,
                        body=body,
                        product=product,
                        created_ts=now)
    db.session.add(question)
    db.session.commit()
    return generate_success_response_from_obj(obj=question, obj_name='question')


@client.route('/questions/<int:question_id>/answers/create', methods=['POST'])
@verify_requirements('client.reviews')
@login_required
def route_question_answer_create(question_id):
    # Verify required objects
    question_id = get_required_parameter(request.form, 'question_id')
    body = get_required_parameter(request.form, 'body')
    question = get_required_model_instance_by_id(Question, question_id)

    # Create Answer
    now = datetime.datetime.utcnow()
    answer = Answer(user=current_user,
                    body=body,
                    question=question,
                    created_ts=now)
    db.session.add(answer)
    db.session.commit()
    return generate_success_response_from_obj(obj=answer, obj_name='answer')


@client.route('/products/<int:product_id>/reviews/search')
@verify_requirements('client.reviews')
def route_product_review_search(product_id):
    query = get_required_parameter(request.args, 'query')
    async = request.form.get('async')
    reviews = Review.query.whoosh_search(query).filter_by(product_id=product_id).all()
    if async:
        return render_template('simple/partials/search/results.html',
                               product_id=product_id,
                               reviews=reviews,
                               query=query)
    return render_template('simple/partials/search/results.html',
                           product_id=product_id,
                           reviews=reviews,
                           query=query)


@client.route('/products/<int:product_id>/reviews/create', methods=['POST'])
@verify_requirements('client.product_review_create')
@limiter.limit(Constants.RATELIMIT_CREATE_OBJECTS)
def route_product_review_create(product_id):
    # Verify required objects
    product = get_required_model_instance_by_id(Product, product_id)

    user = get_real_or_anonymous_user()
    if not user.is_authenticated():
        validate_or_create_user(user)

    # Get the rest of the parameters
    body = request.form.get('body')

    star_rating = request.form.get('star_rating')
    if star_rating and star_rating.isdigit():
        verify_required_condition(condition=int(star_rating) in range(1, 6),
                                  error_msg=ExceptionMessages.STAR_RATING_BETWEEN_1_5)

    # save image - either from the ready form image_url field or from the field file...
    # TODO: Javascript upload picture async
    image_url = request.form.get('image_url')
    if not image_url and request.files:
        file = request.files.get('image')
        filename = review_images.save(file)
        image_url = g.config.get('OPINEW_API_SERVER') + url_for('media.get_review_image', filename=filename)

    # Create Review
    review = create_review(product=product, user=user, body=body, star_rating=star_rating, image_url=image_url)

    return generate_success_response_from_obj(obj=review, obj_name='review')


@client.route('/reviews/<int:review_id>')
@verify_requirements('client.reviews')
def route_review(review_id):
    review = get_required_model_instance_by_id(Review, review_id)
    return render_template('shop_admin/view_review.html',
                           review=review,
                           page_title='Review by %s about %s' % (review.user_name, review.product.name),
                           page_description=review.body,
                           page_image=review.image_url)


# Override some of the Flask-Security Functionality to support natively UserLegacy
# Can be found in venv/local/lib/python2.7/site-packages/flask_security/views.py
@client.route('/register', methods=['GET', 'POST'])
def register():
    register_user_form = ExtendedRegisterForm(request.form)
    return render_template('security/register_user.html',
                           register_user_form=register_user_form)