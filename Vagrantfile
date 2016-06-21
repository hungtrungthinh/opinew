# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|

  config.vm.box = "ubuntu/trusty64"

  config.vm.network "forwarded_port", guest: 5000, host: 5000
  config.vm.synced_folder ".", "/var/www/opinew.com"

  config.vm.provider "virtualbox" do |vb|
     # Customize the amount of memory on the VM:
     vb.memory = 2048
     vb.cpus = 4
  end

  config.vm.provision "shell", inline: <<-SHELL
    sudo apt-get update
    sudo apt-get install -y python-pip python-virtualenv python-dev libxml2-dev libxslt1-dev nginx uwsgi uwsgi-plugin-python curl libffi-dev rabbitmq-server postgresql postgresql-contrib python-psycopg2 libpq-dev screen amqp-tools postgresql-server-dev-9.3 amqp-tools sshpass libtiff5-dev libjpeg8-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python-tk
    
    # Create venv
    cd /var/www/opinew.com
    if [ ! -d "venv" ]; then
      virtualenv venv
      source venv/bin/activate
      pip install -r requirements.txt
    fi
    
    # Create db
    sudo -u postgres psql -c "CREATE USER opinew_user WITH PASSWORD '"'Opinu@m4d4f4k4!'"';"
    sudo -u postgres psql -c "CREATE DATABASE opinew WITH ENCODING 'UTF8'"
    
    # Create tables
    source venv/bin/activate
    # python create_tables.py
    
    # allow ssh access to upstream
    cp opinew_aws.pem ~/.ssh/
    
    # Populate from upstream
    ssh opinew_server@opinew.com <<'ENDSSH'
        export PGPASSWORD='Opinu@m4d4f4k4!'
        pg_dump -U opinew_user -h localhost opinew > ~/dbexport.pgsql
ENDSSH
    scp opinew_server@opinew.com:/home/opinew_server/dbexport.pgsql ./

    export PGPASSWORD='Opinu@m4d4f4k4!'
    psql -U opinew_user -h localhost opinew < dbexport.pgsql
  SHELL
end
