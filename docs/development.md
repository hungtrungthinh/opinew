## I am ... Product Developer

### How do I get the code?

    $ git clone https://github.com/danieltcv/opinew_ecommerce_api

### How do I setup my environment?
You development machine needs to have:
* [Vagrant](https://www.vagrantup.com/downloads.html)
* [VirtualBox](https://www.virtualbox.org/wiki/Downloads)
* [Ansible](https://www.ansible.com/)
* [PyCharm](https://www.jetbrains.com/pycharm/) |
[Atom](https://atom.io/) | [Vim](http://www.vim.org/) | [butterflies](https://xkcd.com/378/)
* [Chrome](https://www.google.com/chrome/) | [Firefox](https://www.mozilla.org/en-GB/firefox/new/)

Then to setup the machine, get into the workdir of the code and execute:

    vagrant up

This should automatically start, provision dev environment. You can edit files
in the web application and it will automatically refresh the development server.

### How is code organized on a high level?
The web application is modeled as a Model-View-Controller architecture. Models represent business data structure and usually correspond to database tables. Controllers are responsible for business logic and are usually mapped to routes. Views display the content usually as html templates.

Users interacts with views, views send information to controllers which send instructions to models. Whatever doesn't need to be done in a request lifetime (e.g. sending an email, external API request) is put on a queue for execution asyncronously and the scheduling is also done by controllers.

### Where can I see some small issues/features/bugs to get started?
Look for `bitesize` label in the issue tracker.

### Where is the documentation for specific parts?
In the main repository `doc/` directory.

### Where do I see code running?
[http://localhost:5000/](http://localhost:5000/) is running `Flask` development server behind a screen session. Any change that you make to files is instantly updated on the server.

### How do I make changes?
Code is shared with the dev machine to the `/vagrant` directory on the guest. Therefore all changes you make will be automatically synced. All commands below assume you are connected to the guest. To do that:

    vagrant ssh dev

### Any style guides? Static analysis?
We do it as part of the build process / CI. Static analysis is shown to catch bugs humans don't.

### How do I monitor logs of the webapp?

    screen -r webapp

You can exit the screen session and leave it running by pressing `Ctrl+A` and then `D`. If you want to kill the instance, just press `Ctrl+C` which will stop the server and the server.

### How do I restart the webapp?
We recommend to always run behind a screen session so that if you disconnect, the code still executes. To do that:

    screen
    cd /vagrant/products/product_reviews
    ./start_webapp.sh

### How do I run tests?

    cd /vagrant/products/product_reviews
    ./run_tests.sh

### How do I do database migrations?

    cd /vagrant/products/product_reviews
    ./upgrade_db.sh

### How do I install pip packages?

    pipi <package>

`pipi` automatically activates the virtual environment inside of `products/product_reviews/webapp`, installs and updates `requirements.txt`.

### How do I install apt-get packages?

    apti <package>

`apti` automatically installs and updates `aptfile` inside of `products/product_reviews/webapp`.

### How do I commit changes?

    git add .
    git commit -m "<Description of the change>"
    git push origin master

If you are commiting to master, `git commit` will run some pre-commit steps like testing with coverage and history of what you have done since the last commit (with particlar notice to `apt-get` and `pip` commands).

### How do I ask for code review?

### What are the requirements for passing a code review?
* Followed style guide
* Test written for functionality
* Test coverage pass

### How do I propose features? How do I file bug reports?

### How do I share a demo version with the team?

      vagrant share

## I am ... Operations

### What is the operations tools used?
* Docker
* Vagrant
* Ansible
* Jenkins
* GitLab
* GrayLog
* Nagios

### How do I manually build containers
To see what will be pushed to production, the development environment also runs the docker container.

[http://localhost:8080/](http://localhost:8080/) is running the latest `Docker` webapp container.

To rebuild the image:

    $ cd /vagrant/products/product_reviews
    $ ./build_dev.sh

### How do I provision production
First of all, download the production archive from [here](https://goo.gl/LYeXmE) and extract it:

    tar xfvz production_access.tar.gz

On your host machine you would need some additional Vagrant plugins for AWS support. Do it:

    vagrant plugin install vagrant-env
    vagrant plugin install vagrant-aws
    vagrant box add dummy https://github.com/mitchellh/vagrant-aws/raw/master/dummy.box
    vagrant up prod --provider=aws


### How do I monitor the servers for performance?

### How do I get notified for errors?

### How do I analyse and monitor usage by users?
Web analytics.

### How to do backups?

### How to do restores?

### How do I do translations?