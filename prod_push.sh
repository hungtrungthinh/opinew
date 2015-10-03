#!/usr/bin/env bash
tar_self() {
    echo  "*** LOCAL: Creating tar of source ***"
    tar -czf opinew_ecommerce_api.tar.gz *   --exclude ".git" \
                               --exclude ".idea" \
                               --exclude "venv" \
                               --exclude "*.pyc"
}

send_tar_prod() {
    if [ -z "$1" ]; then
        >&2 echo "ip address required"
        return 1
    fi
    echo  "*** LOCAL: Send to production server ***"
    scp opinew_ecommerce_api.tar.gz opinew_server@$ip_address:/home/opinew_server/
}

pushprod() {
    if [ -z "$1" ]; then
        >&2 echo "ip address required"
        return 1
    fi
    ip_address=$1
    echo  "*** LOCAL: Handing control to server ***"
    ssh -t opinew_server@$ip_address "mkdir -p ~/opinew_new &&
                                      echo  \"*** Untar to opinew_new ***\" &&
                                      tar xfz opinew_ecommerce_api.tar.gz -C ~/opinew_new &&
                                      rm -rf ~/opinew_ecommerce_api &&
                                      mv ~/opinew_new ~/opinew_ecommerce_api &&
                                      rm -f opinew_ecommerce_api.tar.gz &&
                                      cd opinew_ecommerce_api &&
                                      ln -s ../opinew_venv ./venv &&
                                      source venv/bin/activate &&
                                      pip install -r requirements.txt &&
                                      find ./media -type f -exec chmod 664 {} \; &&
                                      find ./webapp/static -type f -exec chmod 664 {} \; &&
                                      sudo service nginx restart &&
                                      sudo service uwsgi restart"
}

send_update() {
    if [ -z "$1" ]; then
        >&2 echo "ip address required"
        return 1
    fi
    ip_address=$1
    if [ ! "$2" == "--no-test" ]; then
        ./run_tests.py
        if [ $? -eq 1 ]; then
            >&2 echo "ERROR: Tests failed. ABORTING!!!"
            return 1
        fi
    fi
    tar_self
    send_tar_prod "$ip_address"
    pushprod "$ip_address"
    echo  "*** LOCAL: Cleanup ***"
    rm opinew_ecommerce_api.tar.gz
    return 0
}

send_update opinew_api.com $1