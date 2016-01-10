import html2text
import datetime
import traceback
from flask import render_template
from flask_mail import Message
from webapp import mail, models, db


def send_email(recipients, template, template_ctx, subject=None):
    msg = Message()
    msg.subject = subject
    msg.recipients = recipients
    msg.html = render_template(template, **template_ctx)
    msg.body = html2text.html2text(msg.html)
    mail.send(msg)

    sent_email = models.SentEmail(timestamp=datetime.datetime.utcnow(),
                                  recipients=str(recipients),
                                  subject=subject,
                                  template=template,
                                  template_ctx=str(template_ctx),
                                  body=msg.body,
                                  traceback=traceback.format_exc())
    db.session.add(sent_email)
    db.session.commit()
