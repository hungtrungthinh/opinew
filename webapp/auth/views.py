




# from flask import request, redirect, url_for, render_template, flash, session
# from flask.ext.security import login_required, login_user, current_user, logout_user
# from webapp import db, security
# from webapp.auth import auth
# from webapp.models import Shop, User
# from webapp.common import param_required
# from webapp.exceptions import DbException
# from webapp.forms import LoginForm, SignupForm
# from config import Constants




# @auth.route('/signup', methods=['GET', 'POST'])
# def signup():
#     customer_signup_form = SignupForm()
#     if customer_signup_form.validate_on_submit():
#         # Stripe already has validated the card
#         session['business_signed_up'] = True
#         shop_owner = User.get_or_create_by_email(email=customer_signup_form.email.data)
#         shop_owner.stripe_token = param_required('stripe_token', request.form)
#         shop = Shop()
#         shop.owner = shop_owner
#         db.session.add(shop)
#         db.session.commit()
#         login_user(shop_owner)
#         return redirect(url_for('.install', ref='internal'))
#     return render_template('signup.html', customer_signup_form=customer_signup_form)
#
#
# @auth.route('/signup_user', methods=['GET', 'POST'])
# def signup_user():
#     if current_user.is_authenticated():
#         return redirect(request.referrer or url_for('.shop_admin'))
#     signup_form = SignupForm()
#     if signup_form.validate_on_submit():
#         email = request.form.get('email')
#         password = request.form.get('password')
#         name = request.form.get('name')
#         registered_user = User.query.filter_by(email=email).first()
#         if registered_user:
#             flash('User with email %s already exist.' % email)
#             return redirect(url_for('.signup'))
#         user = User(email=email, password=password, name=name, role=Constants.REVIEWER_ROLE)
#         db.session.add(user)
#         db.session.commit()
#         login_user(user)
#         next_param = request.form.get('next')
#         return redirect(next_param or url_for('.home'))
#     return render_template('signup_user.html', signup_form=signup_form)
#
#
# @auth.route('/login', methods=['GET', 'POST'])
# def login():
#     if current_user.is_authenticated():
#         return redirect(request.referrer or url_for('.shop_admin'))
#     login_form = LoginForm()
#     if login_form.validate_on_submit():
#         email = request.form.get('email')
#         password = request.form.get('password')
#         registered_user = User.query.filter_by(email=email).first()
#         if not registered_user:
#             flash('User with email %s does not exist.' % email)
#             return redirect(url_for('.login'))
#         try:
#             registered_user.validate_password(password)
#         except DbException as e:
#             flash(e.message)
#             return render_template('login.html', login_form=login_form)
#         login_user(registered_user)
#         next_param = request.form.get('next')
#         return redirect(next_param or url_for('.index'))
#     return render_template('login.html', login_form=login_form)
#
#
# @auth.route('/logout', methods=['GET'])
# @login_required
# def logout():
#     logout_user()
#     return redirect(url_for('.index'))
#
#
# @auth.route('/logout_from_plugin', methods=['GET'])
# @login_required
# def logout_from_plugin():
#     logout_user()
#     return redirect(request.referrer)
