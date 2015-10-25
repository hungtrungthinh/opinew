import facebook
import requests
from urlparse import parse_qs

class FacebookApi(object):
    FACEBOOK_GRAPH_API_URL_BASE = 'https://graph.facebook.com'

    def __init__(self, config):
        self.graph = facebook.GraphAPI(access_token=config.get('FB_USER_ACCESS_SECRET'))

    def get_profile(self):
        return self.graph.get_object('me')
