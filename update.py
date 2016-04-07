# COPY (select customer.id, user_id, email, is_shop_owner, temp_password, confirmed_at, last_login_at, stripe_customer_id, stripe_subscription_id, subscription.timestamp as subscription_timestamp, plan.name as plan_name from customer, public.user, subscription, plan where customer.user_id=public.user.id and subscription.plan_id=plan.id and subscription.customer_id=customer.id) TO '/tmp/current_customers.csv' DELIMITER ',' CSV HEADER;
from webapp import models, db, create_app

app = create_app("development")

with app.app_context():
    no_shopify_basic = models.Plan.query.filter_by(id=7).first()
    shopify_basic = models.Plan.query.filter_by(id=8).first()
    shopify_simple = models.Plan.query.filter_by(id=9).first()

    # Edit beauty kitchen subscription
    bk_s = models.Subscription.query.filter_by(id=2).first()
    bk_s.stripe_subscription_id = "sub_8EBtDUle9oaBQ2"
    bk_s.plan = shopify_simple
    bk_s.trialed_for = 30
    db.session.add(bk_s)

    # Edit rachel mcmillan subscription
    s2 = models.Subscription.query.filter_by(id=6).first()
    s2.stripe_subscription_id = "sub_8EBoQIKzdvzYtZ"
    s2.plan = shopify_simple
    s2.trialed_for = 30
    db.session.add(s2)

    # Edit white rabbit subscription
    s4 = models.Subscription.query.filter_by(id=7).first()
    s4.stripe_subscription_id = "sub_8EBrRGwWacDbBi"
    s4.plan = shopify_simple
    s4.trialed_for = 30
    db.session.add(s4)

    # Edit lc.carrier@hotmail.com subscription
    s8 = models.Subscription.query.filter_by(id=41).first()
    s8.stripe_subscription_id = "sub_8EC1VOmQdlms6R"
    s8.plan = shopify_simple
    s8.trialed_for = 30
    db.session.add(s8)

    # Edit lc.carrier@hotmail.com subscription
    s8 = models.Subscription.query.filter_by(id=40).first()
    s8.stripe_subscription_id = "sub_8EC4Tygi3o5Mel"
    s8.plan = shopify_simple
    s8.trialed_for = 30
    db.session.add(s8)

    # Edit dianne subscription
    s3 = models.Subscription.query.filter_by(id=21).first()
    s3.stripe_subscription_id = "sub_8EBzEpz1xvUlBX"
    s3.plan = no_shopify_basic
    s3.trialed_for = 27
    db.session.add(s3)

    # Edit cosneta subscription
    s5 = models.Subscription.query.filter_by(id=35).first()
    s5.stripe_subscription_id = "sub_8EByqUCkrrYLXW"
    s5.plan = no_shopify_basic
    s5.trialed_for = 27
    db.session.add(s5)

    # edit vintage kitchen subscription
    vk_s = models.Subscription.query.filter_by(id=36).first()
    vk_s.stripe_subscription_id = "sub_8EBwLZmzJczlm6"
    vk_s.plan = no_shopify_basic
    vk_s.trialed_for = 27
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

    # Create 2 users:
    madeline_u = models.User(email="madeleine@madelnightlights.com.au")
    madeline_c = models.Customer(user=madeline_u,
                                 stripe_customer_id="cus_8EApEJLklCJFkw")

    test_u = models.User(email="aleksey.emko@gmail.com")
    test_c = models.Customer(user=test_u,
                                 stripe_customer_id="cus_8EAt4P3noce59l")

    # Uninstalled and Trialed for
    for cid in [118, 116, 113, 111, 109, 108, 107, 104, 103, 100, 98, 94, 93, 90, 86, 85, 84, 83, 82, 77, 76, 75, 74, 72, 71, 70, 64, 63, 62, 35, 34, 27, 42, 39, 60, 57, 56, 53, 52, 50, 46, 45, 44, 38]:
        c = models.Customer.query.filter_by(id=cid).first()
        c.active = False
        c.subscription[0].plan = None
        c.subscription[0].timestamp = None
        c.subscription[0].stripe_subscription_id = None
        if cid == 35:
            c.subscription[0].trialed_for = 6
        elif cid == 34:
            c.subscription[0].trialed_for = 1
        elif cid == 27:
            c.subscription[0].trialed_for = 1
        elif cid == 38:
            c.subscription[0].trialed_for = 8
        elif cid == 46:
            c.subscription[0].trialed_for = 6
        elif cid == 52:
            c.subscription[0].trialed_for = 7
        elif cid == 44:
            c.subscription[0].trialed_for = 11
        elif cid == 93:
            c.subscription[0].trialed_for = 2
        elif cid == 85:
            c.subscription[0].trialed_for = 14
        elif cid == 74:
            c.subscription[0].trialed_for = 3
        elif cid == 71:
            c.subscription[0].trialed_for = 22
        else:
            c.subscription[0].trialed_for = 0
        db.session.add(c)


    # TRIALED FOR
    import datetime
    now = datetime.datetime.utcnow()
    for sid in [117, 115, 114, 112, 110, 106, 105, 102, 101, 99, 97, 96, 95, 92, 91, 89, 88, 87, 81, 80, 79, 78, 73, 69, 68, 67, 66, 65, 61, 59, 58, 55, 54, 51, 49, 48, 47, 41, 40, 37, 36, 22, 6, 7, 2]:
        c = models.Customer.query.filter_by(id=sid).first()
        s = c.subscription[0]
        started = s.timestamp
        s.trialed_for = (now - started).days
        db.session.add(s)


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
    s7 = models.Subscription(customer=c7, trialed_for=12, stripe_subscription_id="sub_8EBd5TK5w2dSLX")
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
    s8 = models.Subscription(customer=c8, trialed_for=0, stripe_subscription_id="sub_8EBeMCSNWzo2Hg")
    shop5 = models.Shop(owner=u8, name="GftsForAll", domain="gftsforall.myshopify.com", platform=platform_shopify)
    db.session.add(shop5)
    db.session.add(c8)
    db.session.add(s8)

    for s in models.Subscription.query.all():
        shops = s.customer.user.shops
        if shops:
            s.shop = shops[0]
        db.session.add(s)

    db.session.commit()