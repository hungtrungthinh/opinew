from webapp import create_app
from flask.ext.security.utils import encrypt_password
import sensitive

app = create_app('db_dev')
app.app_context().push()

for a in ['DC8E2']:
    print encrypt_password(a)
