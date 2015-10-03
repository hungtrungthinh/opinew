import os
import requests
import urllib
from csv_utf_support import CSVUnicodeWriter
from config import basedir
from webapp.common import random_pwd


with open(os.path.join(basedir, 'init_db', 'User.csv'), mode='w') as users_f:
    csv_w = CSVUnicodeWriter(users_f)
    csv_w.writerow(('id', 'email', 'password', 'name', 'profile_picture_url'))
    for i in range(1, 20):
        rv = requests.get('http://api.randomuser.me/')
        resp = rv.json()['results'][0]['user']
        name = "%s %s" % (resp['name']['first'], resp['name']['last'])
        email = resp['email']
        password = random_pwd()
        img_url = resp['picture']['medium']
        img_name = '%s_%s.jpg' % (i, name.replace(' ', '_').lower())
        urllib.urlretrieve(img_url, os.path.join(basedir, 'media', 'user', img_name))
        csv_w.writerow((str(i), email, password, name.title(), img_name))
