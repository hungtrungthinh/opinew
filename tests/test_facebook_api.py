from async.facebook_api import FacebookApi
from webapp import create_app

app = create_app('db_dev')
app.app_context().push()

fb_api = FacebookApi(app.config)

# TODO: Facebook requires page access token...
# http://aseriesoftubes.com/articles/obtaining-facebook-page-access-tokens-the-4-step-program/
profile = fb_api.get_profile()
print profile