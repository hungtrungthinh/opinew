import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import render_template
from config import Config

def send_mail():
    subject = "Glasgow University Tech Society Meeting"
    sender = Config.EMAIL_ADDRESS
    
    members = models.Member.query.all()
    event = models.Event.query.filter(models.Event.id == request.args.get('event_id')).first()
    
    print("e"+str(event.id))
    # Send the message via local SMTP server.
    # server = smtplib.SMTP('smtp.gmail.com',587)             # gmail port 465 or 587 
    server = smtplib.SMTP_SSL(Config.SMTP_SERVER, 465)               # godaddy
    server.ehlo()                                             # both
    #server.starttls()                                        # gmail
    #server.ehlo()                                            # gmail
    server.login(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)               # both
    
    for m in members:
        recipient = m.email
        req_key = m.write_key

        # Create message container - the correct MIME type is multipart/alternative.
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = recipient

        title = event.title
        description = event.description
        fb_event = event.fb_event
        location = event.location
        time="3rd October, 5 - 9 pm"
        # Create the body of the message (a plain-text and an HTML version).
        text = "Glasgow University Tech Society team has the pleasure of inviting you to a special event.\n\n"+title+"--------------------------------------------------\n\nWhen: "+time+"\nWhere: "+location+"--------------------------------------------------\n"+description+"--------------------------------------------------\n\n"+"To edit your subscription settings, visit: http://www.gutechsoc.com/subscription?email="+recipient+"&req_key="+req_key+"\n"
        html = render_template('email_template.html', 
                           subject = subject, 
                           recipient = recipient, 
                           req_key = req_key,
                           title = title,
                           description = description,
                           fb_event = fb_event,
                           time = time,
                           location = location)

        # Record the MIME types of both parts - text/plain and text/html.
        part1 = MIMEText(text, 'plain')
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
    return "sent!"