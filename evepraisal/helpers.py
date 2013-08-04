import time
import json
from functools import wraps

from flask import g, redirect, url_for, request, flash

from models import Scans
from . import db, cache


def login_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not g.user:
            flash('Login Required.', 'error')
            return redirect(url_for('login', next=request.url))
        return func(*args, **kwargs)
    return decorated_function


def save_result(result, public=True):
    data = json.dumps(result, indent=2)
    user_id = None
    if g.user:
        user_id = g.user.Id
    scan = Scans(
        Data=data,
        Created=int(time.time()),
        BuyValue=result['totals']['buy'],
        SellValue=result['totals']['sell'],
        Public=public,
        UserId=user_id)
    db.session.add(scan)
    db.session.commit()
    return scan.Id


def load_result(result_id):
    try:
        result_id = int(result_id)
    except:
        return

    data = cache.get("results:%s" % result_id)
    if data:
        return data

    q = Scans.query.filter(Scans.Id == result_id)
    if g.user:
        q = q.filter(
            (Scans.UserId == g.user.Id) | (Scans.Public == True))  # noqa
    else:
        q = q.filter(Scans.Public == True)  # noqa

    row = q.first()

    if row:
        data = json.loads(row.Data)
        if 'raw_scan' in data:
            data['raw_paste'] = data['raw_scan']
            del data['raw_scan']

        if row.Public is True:
            cache.set("results:%s" % result_id, data, timeout=600)
        return data


def is_from_igb():
    return request.headers.get('User-Agent', '').find("EVE-IGB") != -1
