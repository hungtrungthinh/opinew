import requests
from config import Constants

GIPHY_URL = "http://api.giphy.com/v1/gifs"


def get_by_query(api_key, search_q, limit=Constants.REVIEWS_PER_PAGE, offset=0):
    r = requests.get(GIPHY_URL + "/search", {"q": search_q, "limit": limit, "offset": offset, "api_key": api_key})
    if r.status_code != 200:
        return {'ERROR': r.text}
    return r.json()


def get_trending(api_key, limit=Constants.REVIEWS_PER_PAGE):
    r = requests.get(GIPHY_URL + "/trending", {"limit": limit, "api_key": api_key})
    if r.status_code != 200:
        return {'ERROR': r.text}
    return r.json()
