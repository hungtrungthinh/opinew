#!venv/bin/python
from webapp import create_app, db
from flask.ext.script import Manager
from flask.ext.migrate import MigrateCommand

app = create_app('production')
manager = Manager(app)
manager.add_command('db', MigrateCommand)


@manager.command
def init_db():
    """
    Drops and re-creates the SQL schema
    """
    db.drop_all()
    db.configure_mappers()
    db.create_all()
    db.session.commit()

if __name__ == '__main__':
    manager.run()
