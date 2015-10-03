#!/usr/bin/env bash
# Constants
USER_NAME=opinew_server
HOME_DIR=/home/${USER_NAME}

echo "Creating user ${USER_NAME}..."
useradd -G sudo -s /bin/bash ${USER_NAME}
passwd ${USER_NAME}
mkdir -p ${HOME_DIR} && cp -r ./ ${HOME_DIR}
chown -R ${USER_NAME}:${USER_NAME} ${HOME_DIR}
sudo su opinew_server
cd

PACKAGES="git python-pip python-virtualenv python-dev nginx uwsgi uwsgi-plugin-python curl"

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

echo "Installing ubuntu packages"
sudo apt-get update
sudo apt-get install -y ${PACKAGES}

echo "Copy ssh keys"
cd ${HOME_DIR}/.ssh
curl -L ${ID_RSA_DW} > id_rsa
curl -L ${ID_RSA_PUB_DW} > id_rsa.pub
eval `ssh-agent`
ssh-add ~/.ssh/id_rsa

echo "Set up required directories"
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

echo "Configure nginx"
sudo bash -c "cat << 'EOF' > /etc/nginx/sites-available/opinew
server {
        listen 80;
        server_tokens off;
        server_name localhost;
        charset utf-8;

        access_log  /var/log/nginx/access.log;
        error_log  /var/log/nginx/error.log;

        location / {
                include uwsgi_params;
                uwsgi_pass unix:${SOCKET_FILE};
        }

        location /static {
                alias ${PROJECT_DIR}/webapp/static;
        }

        location /media {
                alias ${PROJECT_DIR}/media;
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
EOF"
sudo ln -s /etc/uwsgi/apps-available/opinew.ini /etc/uwsgi/apps-enabled/opinew.ini

echo "Open ports"
sudo iptables -I INPUT 1 -p tcp --dport 80 -j ACCEPT

echo "Create db"
cd ${PROJECT_DIR}
./repopulate.py db_prod

echo "Restart services"
sudo service nginx restart
sudo service uwsgi restart

echo "Jenkins"
wget -q -O - https://jenkins-ci.org/debian/jenkins-ci.org.key | sudo apt-key add -
sudo sh -c 'echo deb http://pkg.jenkins-ci.org/debian binary/ > /etc/apt/sources.list.d/jenkins.list'
sudo apt-get update
sudo apt-get install jenkins
sudo /etc/init.d/jenkins start