import twitter


class TwitterApi(object):
    def __init__(self, config):
        self.twitter_api = twitter.Api(consumer_key=config.get('TWITTER_API_KEY'),
                                       consumer_secret=config.get('TWITTER_API_SECRET'),
                                       access_token_key=config.get('TWITTER_APP_ACCESS_TOKEN'),
                                       access_token_secret=config.get('TWITTER_APP_ACCESS_SECRET'))

    def get_mentions(self, search_string):
        statuses = self.twitter_api.GetSearch(term=search_string, count=100)
        return statuses
