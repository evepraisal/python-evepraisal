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
                'contract',
                'dscan',
                'fitting',
                'listing',
                'loot_history',
                'pi',
                'survey_scanner',
                'view_contents',
                'heuristic']:
        for item in result:
            if 'BLUEPRINT COPY' in item.get('details', ''):
                yield item['name'], 0
            else:
                yield item['name'], item.get('quantity', 1)
    elif kind == 'bill_of_materials':
        for item in result:
            yield item['name'], item.get('you', item.get('quantity'))
    elif kind == 'eft':
        yield result['ship'], 1
        for item in result['modules']:
            yield item['name'], item.get('quantity', 1)
            if item.get('ammo'):
                yield item['ammo'], 1
    elif kind == 'killmail':
        yield result['victim']['destroyed'], 1
        for item in result['dropped']:
            yield item['name'], item.get('quantity', 1)
        for item in result['destroyed']:
            yield item['name'], item.get('quantity', 1)
    elif kind == 'wallet':
        for item in result:
            if item.get('name'):
                yield item['name'], item.get('quantity', 1)
    else:
        raise ValueError('Invalid kind %s', kind)
