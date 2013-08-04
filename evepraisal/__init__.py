# -*- coding: utf-8 -*-
"""
    Evepraisal
"""
import locale
import json

from flask import Flask, g, session
from flask.ext.cache import Cache
from flask.ext.sqlalchemy import SQLAlchemy
from flaskext.babel import Babel
from flask_openid import OpenID

app = Flask(__name__)

# configuration
app.config['DEBUG'] = True
app.config['VALID_SOLAR_SYSTEMS'] = {
    '-1': 'Trade Hub Regions',
    '30000142': 'Jita',
    '30002187': 'Amarr',
    '30002659': 'Dodixie',
    '30002510': 'Rens',
    '30002053': 'Hek',
}
app.config['TYPES'] = json.loads(open('data/types.json').read())
app.config['USER_AGENT'] = 'Evepraisal/1.0 +http://evepraisal.com/'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../data/scans.db'
app.config['CACHE_TYPE'] = 'memcached'
app.config['CACHE_KEY_PREFIX'] = 'evepraisal'
app.config['CACHE_MEMCACHED_SERVERS'] = ['127.0.0.1:11211']
app.config['CACHE_DEFAULT_TIMEOUT'] = 10 * 60
app.config['TEMPLATE'] = 'sudorandom'
app.config['SECRET_KEY'] = 'SET ME TO SOMETHING SECRET IN THE APP CONFIG!'
app.config['USER_DEFAULT_OPTIONS'] = {'autosubmit': False, 'share': True}

app.config.from_pyfile('application.cfg', silent=True)

locale.setlocale(locale.LC_ALL, '')

oid = OpenID(app)
db = SQLAlchemy(app)
babel = Babel(app)
cache = Cache()
cache.init_app(app)

# Late import so modules can import their dependencies properly
from . import models, views, routes, filters  # NOQA


def ignore_errors(f, *args, **kwargs):
    try:
        f(*args, **kwargs)
    except:
        pass


@app.before_first_request
def before_first_request():
    try:
        models.db.create_all()
    except Exception as e:
        app.logger.error(str(e))

    try:
        ignore_errors(db.engine.execute,
                      'ALTER TABLE Scans ADD COLUMN UserId integer')
    except Exception, e:
        pass


@app.before_request
def before_request():
    g.user = None
    if 'openid' in session:
        g.user = models.Users.query.filter_by(OpenId=session['openid']).first()

    if g.user and not session.get('loaded_options'):
        # Decode options if there are any
        if g.user.Options:
            options = json.loads(g.user.Options)
            session['options'] = options

        session['loaded_options'] = True

    if 'options' not in session:
        session['options'] = app.config['USER_DEFAULT_OPTIONS']
