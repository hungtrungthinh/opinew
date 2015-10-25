import os
from webapp import create_app
from async.twitter_api import TwitterApi
from importers.csv_utf_support import CSVUnicodeWriter

app = create_app('db_dev')
app.app_context().push()

twitter_api = TwitterApi(app.config)
statuses = twitter_api.get_mentions('@beautykitchen')

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