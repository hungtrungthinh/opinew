from async.facebook_api import FacebookApi
from webapp import create_app
from flask.ext.security.utils import encrypt_password

app = create_app('db_dev')
app.app_context().push()

for a in ["Opinu@m4d4f4k4!",
          "Opinu@m4d4f4k4!",
          "JEX9T",
          "K4YNZ",
          "BANLE",
          "ELP2Z",
          "46C9J",
          "G0UT5",
          "MTIBC",
          "A6P1F",
          "B8U68",
          "SIVQJ",
          "1WGT3",
          "JJ057",
          "X7N1P",
          "2HNTF",
          "92CHR",
          "83IOU",
          "RM43T",
          "owner_password",
          "owner_password"]:
    print encrypt_password(a)
