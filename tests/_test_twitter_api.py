import os
import twitter
from webapp import create_app
from importers.csv_utf_support import CSVUnicodeWriter

app = create_app('db_dev')
app.app_context().push()

twitter_api = twitter.Api(consumer_key=app.config.get('TWITTER_API_KEY'),
                          consumer_secret=app.config.get('TWITTER_API_SECRET'),
                          access_token_key=app.config.get('TWITTER_APP_ACCESS_TOKEN'),
                          access_token_secret=app.config.get('TWITTER_APP_ACCESS_SECRET'))
statuses = twitter_api.GetSearch(term='@beautykitchen', count=100)

basedir = os.path.abspath(os.path.dirname(__file__))
file_path = os.path.join(basedir, 'test_files', 'twitter_beauty_kitchen.csv')

with open(file_path, 'w') as f:
    csv_writer = CSVUnicodeWriter(f, lineterminator='\n')
    for status in statuses:
        if status.retweeted_status:
            row = [status.retweeted_status.text]
        else:
            row = [status.text]
        csv_writer.writerow(row)
