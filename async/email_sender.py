import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import render_template, current_app
from config import Config
from webapp import create_app

def send_mail(recipient, subject, template, template_context, text_only=''):
    # Create dummy app
    app = create_app('dummy')
    app.app_context().push()
    sender = current_app.config.get('EMAIL_ADDRESS')
    sender_pwd = current_app.config.get('EMAIL_PASSWORD')
    
    # Send the message via local SMTP server.
    # server = smtplib.SMTP('smtp.gmail.com',587)             # gmail port 465 or 587 
    server = smtplib.SMTP_SSL(Config.SMTP_SERVER, 465)        # godaddy
    server.ehlo()                                             # both
    #server.starttls()                                        # gmail
    #server.ehlo()                                            # gmail
    server.login(sender, sender_pwd)                          # both

    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    # Create the body of the message (a plain-text and an HTML version).
    html = render_template("email/%s" % template, **template_context)

    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(text_only, 'plain')
    part2 = MIMEText(html, 'html')

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    msg.attach(part1)
    msg.attach(part2)

    # sendmail function takes 3 arguments: sender's address, recipient's address
    # and message to send - here it is sent as one string.
    try:
        server.sendmail(sender, recipient, msg.as_string())
        print "Sent email to " + recipient
    except smtplib.SMTPException:
        print "Failed to send email to " + recipient
    server.quit()

if __name__ == '__main__':
    recipient = 'danieltcv@gmail.com'
    subject = "Review request from Opinew"
    template = 'review_order.html'

    send_mail(recipient, subject, template, {'subject': subject})