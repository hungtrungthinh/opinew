import httplib
import datetime
from webapp import db, models
from flask import g, url_for
from flask.ext.security.utils import encrypt_password
from webapp.exceptions import RequirementException, ExceptionMessages
from config import Constants
from webapp import common
from assets import strings


class Dao(object):
    @classmethod
    def get_by_id(cls, instance_id):
        raise NotImplementedError()


class SqlAlchemyDao(Dao):
    model = None

    @classmethod
    def create(cls, **kwargs):
        return cls.model(**kwargs)

    @classmethod
    def get_by_id(cls, instance_id):
        return cls.model.query.filter_by(id=instance_id).first()

    @classmethod
    def get_by_name(cls, name):
        cls.model.query.filter_by(name=name).first()


class OpinewSQLAlchemyFacade(object):
    def add(self, instance):
        db.session.add(instance)

    def push(self):
        db.session.commit()

    class Role(SqlAlchemyDao):
        model = models.Role

    class User(SqlAlchemyDao):
        model = models.User

        @classmethod
        def get_or_create_shop_owner(cls, email, **kwargs):
            shop_owner = cls.get_by_email(email=email)
            if shop_owner:
                shop_owner.is_shop_owner = True
                role = OpinewSQLAlchemyFacade.Role.get_by_name(name=Constants.SHOP_OWNER_ROLE)
                if role:
                    shop_owner.roles.append(role)
                return shop_owner
            else:
                return cls.create(email=email,
                                  password=common.generate_temp_password(),
                                  is_shop_owner=True,
                                  **kwargs)

        @classmethod
        def create(cls, **kwargs):
            cls._prepare_user_kwargs(kwargs)
            existing_legacy_user = cls._check_for_existing_legacy_user(**kwargs)
            if existing_legacy_user:
                return cls._create_from_legacy(existing_legacy_user, **kwargs)
            return cls.model(**kwargs)

        @classmethod
        def create_legacy(cls, email, **kwargs):
            existing_user = cls.get_by_email(email)
            if existing_user:
                return existing_user
            return cls.model(email=email, is_legacy=True, **kwargs)

        @classmethod
        def _check_for_existing_legacy_user(cls, **kwargs):
            email = kwargs.get('email')
            existing_user = cls.get_by_email(email)
            if existing_user:
                if existing_user.is_legacy:
                    return existing_user
                raise RequirementException(message=ExceptionMessages.USER_EXISTS.format(user_email=email),
                                           error_code=httplib.BAD_REQUEST,
                                           error_category='warning')

        @classmethod
        def _prepare_user_kwargs(cls, kwargs):
            kwargs['password'] = encrypt_password(kwargs.get('password'))
            for k in ['csrf_token', 'submit', 'password_confirm', 'next']:
                if k in kwargs:
                    kwargs.pop(k)

        @classmethod
        def _create_from_legacy(cls, existing_user, **kwargs):
            existing_user.is_legacy = False
            for k, w in kwargs.iteritems():
                setattr(existing_user, k, w)
            return existing_user

        @classmethod
        def get_by_email(cls, email):
            return cls.model.query.filter_by(email=email).first()

    class Shop(SqlAlchemyDao):
        model = models.Shop

        @classmethod
        def create(cls, **kwargs):
            instance = cls.model(**kwargs)
            cls._create_initial_next_actions(instance)
            return instance

        @classmethod
        def _create_initial_next_actions(cls, shop):
            OpinewSQLAlchemyFacade.NextAction.create_setup_plugin(shop)
            OpinewSQLAlchemyFacade.NextAction.create_setup_billing(shop)
            OpinewSQLAlchemyFacade.NextAction.create_change_password(shop)

        @classmethod
        def get_by_domain(cls, domain):
            cls.model.query.filter_by(domain=domain).first()

    class Platform(SqlAlchemyDao):
        model = models.Platform

    class Product(SqlAlchemyDao):
        model = models.Product

        @classmethod
        def get_by_platform_product_id(cls, platform_product_id):
            return cls.model.query.filter_by(platform_product_id=platform_product_id).first()

    class Order(SqlAlchemyDao):
        model = models.Order

        @classmethod
        def get_by_platform_order_id(cls, platform_order_id):
            cls.model.query.filter_by(platform_order_id=platform_order_id).first()

    class ProductVariant(SqlAlchemyDao):
        model = models.ProductVariant

        @classmethod
        def get_by_platform_variant_id(cls, platform_variant_id):
            return cls.model.query.filter_by(platform_variant_id=platform_variant_id).first()

    class NextAction(SqlAlchemyDao):
        model = models.NextAction

        @classmethod
        def create_setup_plugin(cls, shop):
            now = datetime.datetime.utcnow()
            return cls.create(
                shop=shop,
                timestamp=now,
                identifier=Constants.NEXT_ACTION_ID_SETUP_YOUR_SHOP,
                title=strings.NEXT_ACTION_SETUP_YOUR_SHOP,
                url=url_for('client.setup_plugin', shop_id=shop.id),
                icon=Constants.NEXT_ACTION_SETUP_YOUR_SHOP_ICON,
                icon_bg_color=Constants.NEXT_ACTION_SETUP_YOUR_SHOP_ICON_BG_COLOR
            )

        @classmethod
        def create_setup_billing(cls, shop):
            now = datetime.datetime.utcnow()
            return cls.create(
                timestamp=now,
                shop=shop,
                identifier=Constants.NEXT_ACTION_ID_SETUP_BILLING,
                title=strings.NEXT_ACTION_SETUP_BILLING,
                url="javascript:showTab('#account');",
                icon=Constants.NEXT_ACTION_SETUP_BILLING_ICON,
                icon_bg_color=Constants.NEXT_ACTION_SETUP_BILLING_ICON_BG_COLOR
            )

        @classmethod
        def create_change_password(cls, shop):
            now = datetime.datetime.utcnow()
            return cls.create(
                timestamp=now,
                shop=shop,
                identifier=Constants.NEXT_ACTION_ID_CHANGE_YOUR_PASSWORD,
                title=strings.NEXT_ACTION_CHANGE_YOUR_PASSWORD,
                url=url_for('security.change_password'),
                icon=Constants.NEXT_ACTION_CHANGE_YOUR_PASSWORD_ICON,
                icon_bg_color=Constants.NEXT_ACTION_CHANGE_YOUR_PASSWORD_ICON_BG_COLOR
            )

    class Customer(SqlAlchemyDao):
        model = models.Customer

        @classmethod
        def create(cls, **kwargs):
            payment = g.payment
            instance = cls.model(**kwargs)
            payment.create_customer(instance)
            return instance

    class Plan(SqlAlchemyDao):
        model = models.Plan

    class Subscription(SqlAlchemyDao):
        model = models.Subscription

        @classmethod
        def create(cls, customer, plan, shop):
            payment = g.payment
            existing_subscription = cls.get_by_customer_and_shop(customer=customer, shop=shop)
            if existing_subscription:
                payment.create_subscription_from_existing(existing_subscription)
            instance = cls(customer=customer, plan=plan, shop=shop)
            instance.timestamp = datetime.datetime.utcnow()
            instance = payment.create_subscription(instance, customer, plan)
            return instance

        @classmethod
        def update(cls, instance, plan):
            payment = g.payment
            instance = payment.update_subscription(instance, plan)
            instance.plan = plan
            return instance

        @classmethod
        def cancel(cls, instance):
            payment = g.payment
            now = datetime.datetime.utcnow()
            trialed_for = (now - instance.timestamp).days
            instance.trialed_for = 30 if trialed_for > 30 else trialed_for
            payment.cancel_subscription(instance)
            instance.plan = None
            instance.timestamp = None
            return instance

        @classmethod
        def get_by_customer_and_shop(cls, customer, shop):
            return cls.model.query.filter_by(customer=customer, shop=shop).first()
