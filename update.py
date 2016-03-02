from webapp import models, db

no_shopify_basic = models.Plan.query.filter_by(id=7).first()
shopify_basic = models.Plan.query.filter_by(id=8).first()
shopify_simple = models.Plan.query.filter_by(id=9).first()

# Edit beauty kitchen subscription
bk_s = models.Subscription.query.filter_by(id=2).first()
bk_s.stripe_subscription_id = "sub_7zwZj4A8UI8wfO"
bk_s.plan = shopify_basic
bk_s.trialed_for = 27
db.session.add(bk_s)

# Edit rachel mcmillan subscription
s2 = models.Subscription.query.filter_by(id=6).first()
s2.stripe_subscription_id = "sub_7zwjlkSCFcRpk5"
s2.plan = shopify_basic
s2.trialed_for = 27
db.session.add(s2)

# Edit white rabbit subscription
s4 = models.Subscription.query.filter_by(id=7).first()
s4.stripe_subscription_id = "sub_7zwrARQKECOaD2"
s4.plan = shopify_basic
s4.trialed_for = 27
db.session.add(s4)

# Edit dianne subscription
s3 = models.Subscription.query.filter_by(id=21).first()
s3.stripe_subscription_id = "sub_7lbqJrFVOcOTb8"
s3.plan = no_shopify_basic
s3.trialed_for = 27
db.session.add(s3)

# Edit cosneta subscription
s5 = models.Subscription.query.filter_by(id=35).first()
s5.stripe_subscription_id = "sub_7sOT2dWsEgCOy6"
s5.plan = no_shopify_basic
s5.trialed_for = 21
db.session.add(s5)

# edit vintage kitchen subscription
vk_s = models.Subscription.query.filter_by(id=36).first()
vk_s.stripe_subscription_id = "sub_7sj5kW20MDeWq3"
vk_s.plan = no_shopify_basic
db.session.add(vk_s)


# Cancel customers
c1 = models.Customer.query.filter_by(id=39).first()
c1.stripe_customer_id = "cus_7zx2uFwlgjr9KR"
db.session.add(c1)

c2 = models.Customer.query.filter_by(id=42).first()
c2.stripe_customer_id = "cus_7zx5mITsKeTZyi"
db.session.add(c2)

c3 = models.Customer.query.filter_by(id=27).first()
c3.stripe_customer_id = "cus_7zxDyPLgVmd09B"
db.session.add(c3)

c4 = models.Customer.query.filter_by(id=34).first()
c4.stripe_customer_id = "cus_7zxFZlJeoLHyE8"
db.session.add(c4)

c5 = models.Customer.query.filter_by(id=35).first()
c5.stripe_customer_id = "cus_7zxGaoutiZyLUX"
db.session.add(c5)

for cid in [38, 39, 42, 45, 46, 50, 53, 56, 57, 60, 27, 34, 35, 62, 63, 52, 64]:
    c = models.Customer.query.filter_by(id=cid).first()
    c.active = False
    c.subscription[0].plan = None
    c.subscription[0].timestamp = None
    c.subscription[0].stripe_subscription_id = None
    if cid == 35:
        c.subscription[0].trialed_for = 5
    elif cid == 38:
        c.subscription[0].trialed_for = 8
    elif cid == 46:
        c.subscription[0].trialed_for = 6
    elif cid == 52:
        c.subscription[0].trialed_for = 6
    else:
        c.subscription[0].trialed_for = 0
    db.session.add(c)


# TRIALED FOR
import datetime
now = datetime.datetime.utcnow()
for sid in [39, 40, 43, 46, 47, 48, 50, 51, 53, 54, 57, 58, 60]:
    c = models.Subscription.query.filter_by(id=sid).first()
    started = c.timestamp
    c.trialed_for = (now - started).days
    db.session.add(c)


# Re-Create users/customers/shops
platform_shopify = models.Platform.query.filter_by(id=2).first()
u6 = models.User(email="oren.harris@shopify.com",
                 is_shop_owner=True)
c6 = models.Customer(user=u6,
                     stripe_customer_id = "cus_7zxI67OcVBSoUB",
                     active=True)
s6 = models.Subscription(customer=c6, trialed_for=30)
shop2 = models.Shop(owner=u6, name="appstest2", domain="appstest2.myshopify.com", platform=platform_shopify)
db.session.add(shop2)
shop3 = models.Shop(owner=u6, name="Oren Harris's Store", domain="oren-harriss-store.myshopify.com", platform=platform_shopify)
db.session.add(shop3)
db.session.add(c6)
db.session.add(s6)

# daniel@opinew.com    -- cus_7zxLWvc4scexXy
u7 = models.User.query.filter_by(id=1).first()
u7.is_shop_owner = True
c7 = models.Customer(user=u7,
                     stripe_customer_id = "cus_7zxLWvc4scexXy",
                     active=True)
s7 = models.Subscription(customer=c7, trialed_for=12)
shop4 = models.Shop(owner=u7, name="danisfishandchips", domain="danisfishandchips.myshopify.com", platform=platform_shopify)
db.session.add(shop4)
db.session.add(c7)
db.session.add(s7)

# chavcho93@gmail.com  -- cus_7zxMluF175FLWT
u8 = models.User.query.filter_by(id=228).first()
u8.is_shop_owner = True
c8 = models.Customer(user=u8,
                     stripe_customer_id = "cus_7zxMluF175FLWT",
                     active=True)
s8 = models.Subscription(customer=c8, trialed_for=0)
shop5 = models.Shop(owner=u8, name="GftsForAll", domain="gftsforall.myshopify.com", platform=platform_shopify)
db.session.add(shop5)
db.session.add(c8)
db.session.add(s8)

for s in models.Subscription.query.all():
    shops = s.customer.user.shops
    if shops:
        s.shop = shops[0]
    db.session.add(s)
