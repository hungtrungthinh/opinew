#!venv/bin/python
from webapp import create_app

if __name__ == '__main__':
    app = create_app('dev')
    app.run(host='0.0.0.0')
