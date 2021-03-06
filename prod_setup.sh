#!/usr/bin/env bash
# Constants
USER_NAME=opinew_server
HOME_DIR=/home/${USER_NAME}

echo "Creating user ${USER_NAME}..."
useradd -G sudo -s /bin/bash ${USER_NAME}
passwd ${USER_NAME}
mkdir -p ${HOME_DIR} && cp -r ./ ${HOME_DIR}
chown -R ${USER_NAME}:${USER_NAME} ${HOME_DIR}
sudo su ${USER_NAME}
cd

PACKAGES="git python-pip python-virtualenv python-dev nginx uwsgi uwsgi-plugin-python curl libffi-dev rabbitmq-server postgresql postgresql-contrib python-psycopg2 libpq-dev screen libtiff5-dev libjpeg8-dev zlib1g-dev libfreetype6-dev liblcms2-dev libxml2 libxml2-dev libxslt1-dev python-dev libwebp-dev tcl8.6-dev tk8.6-dev python-tk"

SOCKETS_DIR=${HOME_DIR}/sockets
SOCKET_FILE=${SOCKETS_DIR}/opinew.sock
DB_DIR=${HOME_DIR}/db

PROJECT_NAME=opinew_ecommerce_api
GIT_REPO=git@github.com:danieltcv/${PROJECT_NAME}.git
PROJECT_DIR=${HOME_DIR}/${PROJECT_NAME}
VENV_DIR=${HOME_DIR}/opinew_venv
VENV_SHORTCUT=${PROJECT_DIR}/venv

ID_RSA_PUB_DW="https://drive.google.com/uc?export=download&id=0B_mzL8Vwx1yObDdSdHpadWVqbDg"
ID_RSA_DW="https://drive.google.com/uc?export=download&id=0B_mzL8Vwx1yOaDdIVS11dWRSc3M"

echo "Disable password for sudo"
sudoers_file="/etc/sudoers"
sudo sh -c "echo \"%sudo   ALL=(ALL) NOPASSWD: ALL\" >> $sudoers_file"

echo "Installing ubuntu packages"
sudo apt-get update
sudo apt-get install -y ${PACKAGES}

echo "Copy ssh keys"
mkdir -p ${HOME_DIR}/.ssh
cd ${HOME_DIR}/.ssh
curl -L ${ID_RSA_DW} > id_rsa
curl -L ${ID_RSA_PUB_DW} > id_rsa.pub
chmod 600 id_rsa
eval $(ssh-agent)
ssh-add ~/.ssh/id_rsa

echo "Set up required directories"
cd ${HOME_DIR}
mkdir ${SOCKETS_DIR}
touch ${SOCKETS_DIR}/opinew.sock
sudo chown www-data:www-data ${SOCKET_FILE}
sudo chown www-data:www-data ${SOCKETS_DIR}
mkdir ${DB_DIR}

echo "Clone project repisitory"
git clone ${GIT_REPO}

echo "Set up virtual environment"
virtualenv ${VENV_DIR}
ln -s ${VENV_DIR} ${VENV_SHORTCUT}
cd ${PROJECT_DIR}
source venv/bin/activate
pip install -r requirements.txt

echo
echo "========================================================================="
echo "== Installing https certificate"
echo "========================================================================="
echo

cd ${PROJECT_DIR}/install/cert
cat opinew_com.crt COMODORSADomainValidationSecureServerCA.crt COMODORSAAddTrustCA.crt AddTrustExternalCARoot.crt >> cert_chain.crt
sudo cp cert_chain.crt "/etc/ssl/"
sudo cp opinew_com.key "/etc/ssl/"
sudo rm cert_chain.crt
cd ${PROJECT_DIR}
echo
echo "========================================================================="
echo "== Create HTTPS config file for nginx"
echo "========================================================================="
echo
sudo bash -c "cat << 'EOF' > /etc/nginx/sites-available/opinew
server {
       listen         80;
       server_name    opinew.com;
       return         301 https://\$server_name\$request_uri;
}

server {
        listen 443;
        ssl on;
        ssl_certificate    /etc/ssl/cert_chain.crt;
        ssl_certificate_key    /etc/ssl/opinew_com.key;
        server_tokens off;
        server_name opinew.com;
        charset utf-8;

        client_max_body_size 5M;

        access_log  /var/log/nginx/access.log;
        error_log  /var/log/nginx/error.log;

        if (\$host = 'www.opinew.com' ) {
          rewrite  ^/(.*)$  https://opinew.com/\$1  permanent;
        }

        location / {
                include uwsgi_params;
                uwsgi_pass unix:/home/opinew_server/sockets/opinew.sock;
        }

        location /static {
                alias /home/opinew_server/opinew_ecommerce_api/webapp/static;
        }
}
EOF"

sudo rm /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/opinew /etc/nginx/sites-enabled/opinew

echo "Set up uwsgi"
sudo bash -c "cat << 'EOF' > /etc/uwsgi/apps-available/opinew.ini
[uwsgi]
vhost = true
socket = ${SOCKET_FILE}
venv = ${VENV_SHORTCUT}
chdir = ${PROJECT_DIR}
module = webapp.production
callable = app
plugins = python
lazy = true
lazy-apps = true
EOF"
sudo ln -s /etc/uwsgi/apps-available/opinew.ini /etc/uwsgi/apps-enabled/opinew.ini

echo "Open ports"
sudo iptables -I INPUT 1 -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 1 -p tcp --dport 443 -j ACCEPT

echo "Create db"
cd ${PROJECT_DIR}
sudo su - postgres
createuser -P opinew_user
createdb opinew
exit
# ./repopulate.py db_prod

echo "Restart services"
sudo service nginx restart
sudo service uwsgi restart

echo "Jenkins"
wget -q -O - https://jenkins-ci.org/debian/jenkins-ci.org.key | sudo apt-key add -
sudo sh -c 'echo deb http://pkg.jenkins-ci.org/debian binary/ > /etc/apt/sources.list.d/jenkins.list'
sudo apt-get update
sudo apt-get install jenkins
sudo /etc/init.d/jenkins start
