# Opinew Ecommerce API

Contains the Opinew ecommerce API and front end rendering of the HTML plugin and web review posting. 

## Development Set Up

Create python virtual environment, install required packages and populate the database with some initial data for dev purposes.

1. Install the following packages (ubuntu 12.04 and 14.04):

    sudo apt-get update
    sudo apt-get install git python-pip python-virtualenv python-dev nginx uwsgi uwsgi-plugin-python curl libffi-dev rabbitmq-server postgresql postgresql-contrib python-psycopg2 libpq-dev


1. Set up a virtual environment

    virtualenv venv
    venv/bin/activate
    pip install -r requirements.txt
    
1. Set up postgres database

1. Initialize database

    ./run_development.py db init
    
## Changes

If you change the database, first let alembic write a migration:

    ./run_development.py db migrate
    
Then execute the upgrade of your database

    ./run_development.py db upgrade

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

    ssh opinew_server@opinew.com

1. Dump the db

    pg_dump -U opinew_user -h localhost opinew > ~/dbexport.pgsql

1. Back on local, copy

    scp opinew_server@opinew.com:/home/opinew_server/dbexport.pgsql ./

1. Recreate db - Disconnect from all db instances, login as postgres user and recreate opinew
    
    sudo su - postgres
    dropdb opinew
    createdb opinew

1. Import locally 

    psql -U opinew_user -h localhost opinew < dbexport.pgsql
    