from flask import render_template, send_from_directory, redirect, url_for, request, flash, jsonify
from flask.ext.login import login_required, current_user, login_user, logout_user
from sqlalchemy import and_
from webapp import login_manager
from webapp.forms import LoginForm, ReviewForm
from webapp.client import client
from webapp.models import Shop, Product, User, Role, Order, Review, ShopProduct, Notification
from webapp.common import validate_user_role, get_post_payload, next_is_valid
from webapp.exceptions import ParamException
from config import Config


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


@client.route('/review/<int:order_id>', methods=['GET', 'POST'])
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
    review = order.review
    if review:
        review_form = ReviewForm(formdata=review)
    else:
        review_form = ReviewForm()
    if request.method == 'POST' and review_form.validate_on_submit():
        try:
            payload = get_post_payload()
        except ParamException as e:
            return jsonify({"error": e.message}), 400
        product = Product.get_by_id(order.product_id)
        product.add_review(order=order, payload=payload)
        flash('Review submitted')
        return redirect(url_for('.home'))
    return render_template('web_review/home.html', order=order, review_form=review_form)


login_manager.login_view = "client.login"


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
        if not next_is_valid(next_param):
            flash('Not authenticated to view this page.')
            return redirect(url_for('.shop_admin'))
        return redirect(next_param or url_for('.shop_admin'))
    return render_template('login.html', login_form=login_form)


@login_required
@client.route('/logout', methods=['GET'])
def logout():
    logout_user()
    return redirect(url_for('.shop_admin'))


@client.route('/plugin/shop/<int:shop_id>/product/<int:product_id>/reviews')
def plugin_product_reviews(shop_id, product_id):
    shop = Shop.query.filter_by(id=shop_id).first()
    if not shop:
        return '', 404
    shop_product = ShopProduct.query.filter(
        and_(ShopProduct.shop == shop, ShopProduct.product_id == product_id)).first()
    if not shop_product or not shop_product.product:
        return '', 404
    product = shop_product.product
    reviews = Review.query.filter(and_(Review.product_id == product_id, Review.approved_by_shop)).order_by(
        Review.created_ts.desc()).all()
    return render_template('plugin/plugin.html', product=product, reviews=reviews)


@client.route('/notifications')
@login_required
def get_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).all()
    return render_template('client/notifications.html', notifications=notifications)


@client.route('/media/user/<path:filename>')
def media_user(filename):
    return send_from_directory(Config.UPLOADED_USERPHOTOS_DEST, filename)


@client.route('/media/review/<path:filename>')
def media_review(filename):
    return send_from_directory(Config.UPLOADED_REVIEWPHOTOS_DEST, filename)
