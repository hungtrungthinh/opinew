import html2text
from flask import render_template
from flask_mail import Message
from webapp import mail

def send_email(recipients, template, template_ctx, subject=None):
    msg = Message()
    msg.subject = subject
    msg.recipients = recipients
    msg.html = render_template(template, **template_ctx)
    msg.body = html2text.html2text(msg.html)
    mail.send(msg)
