#!/usr/bin/env bash
update_requirements() {
    echo  "*** LOCAL: Updating requirements ***"
    pip freeze > requirements.txt
}

tar_self() {
    echo  "*** LOCAL: Creating tar of source ***"
    tar cf opinew_ecommerce_api.tar *   --exclude ".git" \
                               --exclude ".idea" \
                               --exclude "venv" \
                               --exclude "*.pyc" \
                               --exclude "*.pgsql" \
                               --exclude "media"
    tar fr opinew_ecommerce_api.tar webapp/media
    gzip opinew_ecommerce_api.tar
}

send_tar_prod() {
    if [ -z "$1" ]; then
        >&2 echo "ip address required"
        return 1
    fi
    echo  "*** LOCAL: Send to production server ***"
    scp -i opinew_aws.pem opinew_ecommerce_api.tar.gz opinew_server@$ip_address:/home/opinew_server/
}

pushprod() {
    if [ -z "$1" ]; then
        >&2 echo "ip address required"
        return 1
    fi
    ip_address=$1
    echo  "*** LOCAL: Handing control to server ***"
    ssh -i opinew_aws.pem -t opinew_server@$ip_address "mkdir -p ~/opinew_new &&
                                      echo  \"*** Untar to opinew_new ***\" &&
                                      tar xfz opinew_ecommerce_api.tar.gz -C ~/opinew_new &&
                                      sudo rm -rf ~/opinew_ecommerce_api &&
                                      mv ~/opinew_new ~/opinew_ecommerce_api &&
                                      rm -f opinew_ecommerce_api.tar.gz &&
                                      cd opinew_ecommerce_api &&
                                      ln -s ../opinew_venv ./venv &&
                                      source venv/bin/activate &&
                                      pip install -r requirements.txt &&
                                      ln -s ../opinew_media ./media &&
                                      find ./media -type f -exec chmod 664 {} \; &&
                                      find ./webapp/static -type f -exec chmod 664 {} \; &&
                                      sudo chown -R www-data ./media &&
                                      sudo chown -R www-data ./webapp/static &&
                                      (screen -S celery -X quit && screen -S celery -d -m ./run_celery.sh) ||
                                            screen -S celery -d -m ./run_celery.sh &&
                                      (screen -S beat -X quit && screen -S beat -d -m ./run_celery_beat.sh) ||
                                            screen -S beat -d -m ./run_celery_beat.sh &&
                                      (screen -S flower -X quit && screen -S flower -d -m ./run_flower.sh) ||
                                            screen -S flower -d -m ./run_flower.sh &&
                                      ./run_production.py db upgrade &&
                                      sudo service nginx restart &&
                                      sudo service uwsgi restart"
}

send_update() {
    if [ -z "$1" ]; then
        >&2 echo "ip address required"
        return 1
    fi
    ip_address=$1
    source venv/bin/activate
#    ./run_tests.py
    if [ $? -eq 1 ]; then
        >&2 echo "ERROR: Tests failed. ABORTING!!!"
        return 1
    else
        update_requirements
        tar_self
        send_tar_prod "$ip_address"
        pushprod "$ip_address"
        echo  "*** LOCAL: Cleanup ***"
        rm opinew_ecommerce_api.tar.gz
        return 0
    fi
}

send_update opinew.com
