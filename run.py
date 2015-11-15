#!venv/bin/python
from webapp import create_app
from flask.ext.script import Manager
from flask.ext.migrate import MigrateCommand

app = create_app('development')
manager = Manager(app)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
