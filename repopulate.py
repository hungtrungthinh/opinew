#!venv/bin/python
import os
import sys
import csv
from flask import current_app
from webapp import models, db, create_app
from config import basedir

def import_tables(db_instance, db_dir):
    for filename in os.listdir(db_dir):
        if not filename.endswith(".csv"):
            continue
        filepath = os.path.join(db_dir, filename)
        with open(filepath, 'r') as csvfile:
            csv_reader = csv.reader(csvfile)
            model_name = filename.split('.')[0]
            headers = csv_reader.next()
            for row in csv_reader:
                record = {}
                for i, column in enumerate(headers):
                    record[column] = row[i]
                model_class = getattr(models, model_name)
                model_instance = model_class().from_repopulate(**record)
                db.session.add(model_instance)
    db_instance.session.commit()

    # Import many-to-many relationships
    for filename in os.listdir(os.path.join(db_dir, 'm_n')):
        filepath = os.path.join(db_dir, 'm_n', filename)
        with open(filepath, 'r') as csvfile:
            csv_reader = csv.reader(csvfile)
            fname = filename.split('.')[0]
            model_one_name, model_two_name = fname.split('_')
            headers = csv_reader.next()
            for row in csv_reader:
                model_one_class = getattr(models, model_one_name)
                model_two_class = getattr(models, model_two_name)
                model_one_instance = model_one_class.query.filter_by(id=row[0]).first()
                model_two_instance = model_two_class.query.filter_by(id=row[1]).first()
                getattr(model_one_instance, headers[1]).append(model_two_instance)
                db_instance.session.add(model_one_instance)
    db_instance.session.commit()


if __name__ == '__main__':
    arguments = sys.argv
    if not len(sys.argv) == 2 or arguments[1] not in ['db_dev', 'db_prod']:
        print "USAGE: ./repopulate.py db_dev|db_prod"
        exit(1)
    option = arguments[1]
    app = create_app(option)

    db.init_app(app)

    try:
        os.remove(app.config.get('DATABASE_LOCATION'))
    except OSError:
        pass

    ###############################
    # INIT DB
    ###############################
    app.app_context().push()
    db.create_all()

    db_dir = os.path.join(basedir, 'install', 'db', current_app.config.get('MODE'))
    import_tables(db, db_dir)
