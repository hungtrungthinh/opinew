from webapp import create_app
from async.email_sender import send_email

if __name__ == '__main__':
    app = create_app('dummy')
    app.app_context().push()
    send_email(recipients=['danieltcv@gmail.com'],
               template='email/new_user.html',
               template_ctx={"subject": "New user",
                             "user_password": "ABCDEF"},
               subject="Welcome to Opinew")