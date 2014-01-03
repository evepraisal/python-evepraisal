from functools import wraps

from flask import g, redirect, url_for, request, flash


def login_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not g.user:
            flash('Login Required.', 'error')
            return redirect(url_for('login', next=request.url))
        return func(*args, **kwargs)
    return decorated_function


def iter_types(kind, result):
    if kind in ['assets',
                'bill_of_materials',
                'dscan',
                'fitting',
                'listing',
                'loot_history',
                'contract']:
        for item in result:
            yield item['name'], item.get('quantity', 1)
    elif kind == 'eft':
        yield result['ship'], 1
        for item in result['modules']:
            yield item['name'], item.get('quantity', 1)
            if item.get('ammo'):
                yield item['ammo'], 1
    else:
        raise ValueError('Invalid kind %s', kind)
