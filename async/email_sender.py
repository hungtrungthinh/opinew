import html2text
import datetime
from flask import render_template
from flask_mail import Message
from webapp import mail, models, db
from webapp.common import random_pwd


def send_email(recipients, template, template_ctx, subject=None, funnel_stream_id=None):
    msg = Message()

    # find recipients and check if they are unsubscribed
    for recipient in recipients:
        user = models.User.query.filter_by(email=recipient).first()
        if not user:
            user = models.UserLegacy.query.filter_by(email=recipient).first()
        if not user:
            user = models.UserLegacy(email=recipient)
            db.session.add(user)
        if user.unsubscribed:
            # Just log that this email is not sent due to unsubscribed status and return
            sent_email = models.SentEmail(timestamp=datetime.datetime.utcnow(),
                                          recipients=str(recipients),
                                          subject="USER HAS UNSUBSCRIBED")
            db.session.add(sent_email)
            db.session.commit()
            return
        if not user.unsubscribe_token:
            user.unsubscribe_token = random_pwd(26)
            db.session.add(user)
            db.session.commit()
        template_ctx['unsubscribe_token'] = user.unsubscribe_token

    # generate tracking pixel
    tracking_pixel_id = random_pwd(26)
    template_ctx['tracking_pixel_id'] = tracking_pixel_id

    # set up email
    msg.subject = subject
    msg.recipients = recipients
    msg.html = render_template(template, **template_ctx)
    msg.body = html2text.html2text(msg.html)

    # Actually send email
    mail.send(msg)

    # find if this is for a shop
    shop_id = None
    if template == 'email/review_order.html':
        if 'shop_name' in template_ctx:
            shop_name = template_ctx['shop_name']
            shop = models.Shop.query.filter_by(name=shop_name).first()
            if shop:
                shop_id = shop.id

    # LOG
    sent_email = models.SentEmail(timestamp=datetime.datetime.utcnow(),
                                  recipients=str(recipients),
                                  subject=subject,
                                  template=template,
                                  template_ctx=str(template_ctx),
                                  body=msg.body,
                                  tracking_pixel_id=tracking_pixel_id,
                                  for_shop_id=shop_id,
                                  funnel_stream_id=funnel_stream_id)

    db.session.add(sent_email)
    db.session.commit()
