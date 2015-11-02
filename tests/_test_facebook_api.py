import facebook
from webapp import create_app

app = create_app('db_dev')
app.app_context().push()

# TODO: Facebook requires page access token...
# http://aseriesoftubes.com/articles/obtaining-facebook-page-access-tokens-the-4-step-program/


fb_graph = facebook.GraphAPI(access_token=app.config.get('FB_USER_ACCESS_SECRET'))
fb_profile = fb_graph.get_object('me')
