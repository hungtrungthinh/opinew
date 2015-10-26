from webapp import create_app
from flask.ext.security.utils import encrypt_password
import sensitive

app = create_app('db_dev')
app.app_context().push()

for a in [sensitive.ADMIN_PASSWORD,
          sensitive.ADMIN_PASSWORD,
          sensitive.TEST_SHOP_OWNER_PASSWORD,
          sensitive.TEST_REVIEWER_PASSWORD,
          sensitive.TEST_REVIEWER_PASSWORD,
          sensitive.TEST_REVIEWER_PASSWORD,
          sensitive.TEST_REVIEWER_PASSWORD,
          sensitive.TEST_REVIEWER_PASSWORD,
          sensitive.TEST_REVIEWER_PASSWORD,
          sensitive.TEST_REVIEWER_PASSWORD,
          sensitive.TEST_REVIEWER_PASSWORD,
          sensitive.TEST_REVIEWER_PASSWORD,
          sensitive.TEST_REVIEWER_PASSWORD,
          sensitive.TEST_REVIEWER_PASSWORD,
          sensitive.TEST_REVIEWER_PASSWORD,
          sensitive.TEST_REVIEWER_PASSWORD,
          sensitive.TEST_REVIEWER_PASSWORD,
          sensitive.TEST_REVIEWER_PASSWORD,
          sensitive.TEST_REVIEWER_PASSWORD,
          sensitive.TEST_SHOP_OWNER_PASSWORD]:
    print encrypt_password(a)
