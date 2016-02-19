from datetime import datetime
from webapp import models, db
from flask import url_for
from assets import strings
from config import Constants

shops = models.Shop.query.all()
now = datetime.utcnow()

# setup next actions
for shop in shops:
    # im1 = models.NextAction(
    #     shop=shop,
    #     timestamp=now,
    #     identifier=Constants.NEXT_ACTION_ID_SETUP_YOUR_SHOP,
    #     title=strings.NEXT_ACTION_SETUP_YOUR_SHOP,
    #     url=url_for('client.setup_plugin', shop_id=shop.id),
    #     icon=Constants.NEXT_ACTION_SETUP_YOUR_SHOP_ICON,
    #     icon_bg_color=Constants.NEXT_ACTION_SETUP_YOUR_SHOP_ICON_BG_COLOR
    # )
    # db.session.add(im1)
    if not shop.owner.customer[0].last4:
        im2 = models.NextAction(
            timestamp=now,
            shop=shop,
            identifier=Constants.NEXT_ACTION_ID_SETUP_BILLING,
            title=strings.NEXT_ACTION_SETUP_BILLING,
            url="javascript:showTab('#account');",
            icon=Constants.NEXT_ACTION_SETUP_BILLING_ICON,
            icon_bg_color=Constants.NEXT_ACTION_SETUP_BILLING_ICON_BG_COLOR
        )
        db.session.add(im2)
    if shop.owner.temp_password:
        im3 = models.NextAction(
            timestamp=now,
            shop=shop,
            identifier=Constants.NEXT_ACTION_ID_CHANGE_YOUR_PASSWORD,
            title=strings.NEXT_ACTION_CHANGE_YOUR_PASSWORD,
            url=url_for('security.change_password'),
            icon=Constants.NEXT_ACTION_CHANGE_YOUR_PASSWORD_ICON,
            icon_bg_color=Constants.NEXT_ACTION_CHANGE_YOUR_PASSWORD_ICON_BG_COLOR
        )
        db.session.add(im3)

# setup new plans

simple_no_shopify = models.Plan(
    name='simple_no_shopify',
    amount=1300,
    description='Simple (no shopify)',
    interval='month',
    trial_period_days=30,
    active=True,
    stripe_plan_id='simple_no_shopify'
)
db.session.add(simple_no_shopify)

shopify_basic = models.Plan(
    name='shopify_basic',
    amount=1900,
    description='Shopify Basic',
    interval='month',
    trial_period_days=30,
    active=True,
    stripe_plan_id='shopify_basic'
)
db.session.add(shopify_basic)

shopify_simple = models.Plan(
    name='shopify_simple',
    amount=0,
    description='Shopify Simple',
    interval='month',
    trial_period_days=30,
    active=True,
    stripe_plan_id='shopify_simple'
)
db.session.add(shopify_simple)

db.session.commit()

