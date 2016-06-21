# Opinew Ecommerce API

Contains the Opinew ecommerce API and front end rendering of the HTML plugin and web review posting. 

## Development Set Up

Create python virtual environment, install required packages and populate the database with some initial data for dev purposes.

1. Install the following packages (ubuntu 12.04 and 14.04):

    sudo apt-get update
    sudo apt-get install git python-pip python-virtualenv python-dev nginx uwsgi uwsgi-plugin-python curl libffi-dev rabbitmq-server postgresql postgresql-contrib python-psycopg2 libpq-dev amqp-tools libtiff5-dev libjpeg8-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python-tk


1. Set up a virtual environment

    virtualenv venv
    venv/bin/activate
    pip install -r requirements.txt
    
1. Set up postgres database
    
    sudo -u postgres psql -c "CREATE USER opinew_user WITH PASSWORD '"'Opinu@m4d4f4k4\!'"';"
    sudo -u postgres psql -c "CREATE DATABASE opinew WITH ENCODING 'UTF8'"

1. Initialize database

    ./run_development.py db init

## Development Set Up (Vagrant)
1. Install Vagrant
1.1. Download from `https://www.vagrantup.com/downloads.html`
1.1. Install with `dpkg -i vagrant-*.deb 
1.1. Run `vagrant init`

1. Setting up PyCharm:
1.1. Change the python interpreter to be inside of Vagrant:

    Project > Settings > Python Interpreters > Add Remote > Vagrant

1.1. On Run/Debug create the following two entries:

`Python > Add new`

    Script: run_development.py
    Params: runserver --host 0.0.0.0 --threaded
    Working Directory: /var/www/opinew.com/

`Python tests > Unit tests`
    
    Test: All in Folder
    Folder: tests
    Working Directory: /var/www/opinew.com/
    Path mappings: <your_local_working_dir>=/var/www/opinew.com  
    
## Changes

If you change the database, first let alembic write a migration:

    ./run_development.py db migrate
    
Then execute the upgrade of your database

    ./run_development.py db upgrade

To manually update the table via SQL

    psql opinew_user  -h 127.0.0.1 -d opinew

To see active connections:
    
    SELECT * FROM pg_stat_activity;

## Translations
Surround code to be translated with {{ gettext() }}

To extract new strings:

    pybabel extract -F babel.cfg -o messages.pot .

To generate new language:

    pybabel init -i messages.pot -d webapp/translations -l pl

If any of these strings change, run:

    pybabel update -i messages.pot -d webapp/translations

Do the translations in `webapp/translations/bg/LC_MESSAGES`

To compile:

    pybabel compile -d webapp/translations

## Run
Once everything is setup, just run with

    ./run_development.py runserver
    
Optionally if you need to run it at 0.0.0.0:

    ./run_development.py runserver --host 0.0.0.0
    
## Run celery manager

    ./run_celery.sh

## Test

    ./run_tests.py

## Production
To set up production, create a server instance and run

    ./prod_setup.sh

## Push to Production
To push to production server `opinew.com`:

    ./prod_push.sh


## Connect to Jenkins

    ssh opinew_server@opinew_api.com -L 8080:localhost:8080 -N
    
## Sync db prod > dev

1. Connect to opinew.com via ssh

    ssh -i opinew_aws.pem opinew_server@opinew.com

1. Dump the db

    pg_dump -U opinew_user -h localhost opinew > ~/dbexport.pgsql

1. Back on local, copy

    scp -i opinew_aws.pem opinew_server@opinew.com:/home/opinew_server/dbexport.pgsql ./

1. Recreate db - Disconnect from all db instances, login as postgres user and recreate opinew
    
    sudo -u postgres psql -c "DROP DATABASE opinew "
    sudo -u postgres psql -c "CREATE DATABASE opinew WITH ENCODING 'UTF8'"

1. Import locally 

    psql -U opinew_user -h localhost opinew < dbexport.pgsql


## Purging

To delete all the tasks:
    
    amqp-delete-queue -q celery
    
## Renew ssl:

Run this command:

    ~/letsencrypt/letsencrypt-auto certonly -a webroot --webroot-path=/usr/share/nginx/html -d opinew.com -d www.opinew.com
