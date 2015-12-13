from flask import current_app
import requests
from config import Constants

def get_by_query(api_key, search_q, limit=Constants.REVIEWS_PER_PAGE, offset=0):
    r = requests.get(current_app.config.get('GIPHY_URL') + "/search", {"q": search_q, "limit": limit, "offset": offset, "api_key": api_key})
    if r.status_code != 200:
        return {'ERROR': r.text}
    return r.json()


def get_trending(api_key, limit=Constants.REVIEWS_PER_PAGE):
    r = requests.get(current_app.config.get('GIPHY_URL') + "/trending", {"limit": limit, "api_key": api_key})
    if r.status_code != 200:
        return {'ERROR': r.text}
    try:
        return r.json()
    except:
        return ''
