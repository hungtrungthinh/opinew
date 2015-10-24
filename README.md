# Opinew Ecommerce API

Contains the Opinew ecommerce API and front end rendering of the HTML plugin 
and web review posting. 

## Set Up

Create python virtual environment, install required packages and populate the
database with some initial data for dev purposes.

    virtualenv venv
    venv/bin/activate
    pip install -r requirements.txt
    ./repopulate

## Run

    ./run.py
    
## Run celery manager

    ./run_celery.sh

## Test

    ./run_tests.py

## Production
To set up production, create a server instance and run

    ./prod_setup


## Connect to Jenkins

    ssh opinew_server@opinew_api.com -L 8080:localhost:8080 -N