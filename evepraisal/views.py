# -*- coding: utf-8 -*-
"""
    An Eve Online Cargo Scanner
"""
import time
import json

from flask import (
    g, flash, request, render_template, url_for, redirect, session,
    send_from_directory, abort)
from sqlalchemy import desc

from helpers import login_required
from parser import parse_paste_items
from estimate import get_market_prices
from models import Appraisals, Users, get_type_by_name
from . import app, db, cache, oid


def match_item_details(kind, result):
    """ Returns a mapping of module name (munged) => module id for all unique
        modules"""
    items = []
    bad_items = []
    if kind in ['assets',
                'bill_of_materials',
                'dscan',
                'fitting',
                'listing',
                'loot_history',
                'contract']:
        for item in result:
            items.append(item['name'])
    elif kind == 'eft':
        result.append(item['ship'])
        for item in result['modules']:
            items.append(item['name'])
            if item.get('ammo'):
                items.append(item['ammo'])
    else:
        raise ValueError('Invalid kind %s', kind)

    name_map = {}
    for item in items:
        details = get_type_by_name(item)
        if details:
            name_map[item] = details
        else:
            bad_items.append(item)

    return [(details['typeID'], name, details)
            for name, details in name_map.items()], bad_items


def estimate_cost():
    """ Estimate Cost of pasted stuff result given by POST[raw_paste].
        Renders HTML """
    raw_paste = request.form.get('raw_paste', '')
    solar_system = request.form.get('market', '30000142')

    if solar_system not in app.config['VALID_SOLAR_SYSTEMS'].keys():
        abort(400)

    kind, result, bad_lines = parse_paste_items(raw_paste)

    # Populate types with pricing data
    item_details, bad_items = match_item_details(kind, result)
    prices = get_market_prices([type_id for type_id, _, _ in item_details],
                               options={'solarsystem_id': solar_system})

    appraisal = Appraisals(Created=int(time.time()),
                           RawInput=raw_paste,
                           Kind=kind,
                           PricesJson=prices,
                           ParsedJson=result,
                           BadLinesJson=bad_lines,
                           Market=solar_system,
                           Public=bool(session['options'].get('share')),
                           UserId=g.user.Id if g.user else None)
    db.session.add(appraisal)
    db.session.commit()

    print dict((col, getattr(appraisal, col)) for col in appraisal.__table__.columns.keys())

    return render_template('results.html',
                           appraisal=appraisal,
                           full_page=request.form.get('load_full'))


def display_result(result_id):
    # TODO: FIX THIS TO WORK WITH THE NEW TABLE
    try:
        result_id = int(result_id)
    except:
        flash('Resource Not Found', 'error')
        return index(), 404

    data = cache.get("results:%s" % result_id)
    if data:
        return data

    q = Appraisals.query.filter(Appraisals.Id == result_id)
    if g.user:
        q = q.filter((Appraisals.UserId == g.user.Id) |
                     (Appraisals.Public == True))  # noqa
    else:
        q = q.filter(Appraisals.Public == True)  # noqa

    appraisal = q.first()

    if not appraisal:
        flash('Resource Not Found', 'error')
        return index(), 404

    if appraisal.Public is True:
        cache.set("results:%s" % result_id, data, timeout=600)

    return render_template('results.html', appraisal=appraisal, full_page=True)


@login_required
def options():
    if request.method == 'POST':
        autosubmit = True if request.form.get('autosubmit') == 'on' else False
        paste_share = True if request.form.get('share') == 'on' else False

        new_options = {
            'autosubmit': autosubmit,
            'share': paste_share,
        }
        session['loaded_options'] = False
        g.user.Options = json.dumps(new_options)
        db.session.add(g.user)
        db.session.commit()
        flash('Successfully saved options.')
        return redirect(url_for('options'))
    return render_template('options.html')


@login_required
def history():
    q = Appraisals.query
    q = q.filter(Appraisals.UserId == g.user.Id)
    q = q.order_by(desc(Appraisals.Created), desc(Appraisals.Id))
    q = q.limit(100)
    results = q.all()

    result_list = []
    for result in results:
        result_list.append({
            'result_id': result.Id,
            'created': result.Created,
        })

    return render_template('history.html', listing=result_list)


def latest(limit):
    if limit > 1000:
        return redirect(url_for('latest', limit=1000))

    result_list = cache.get("latest:%s" % limit)
    if not result_list:
        q = Appraisals.query
        q = q.filter_by(Public=True)  # NOQA
        q = q.order_by(desc(Appraisals.Created), desc(Appraisals.Id))
        q = q.limit(limit)
        results = q.all()

        result_list = []
        for result in results:
            result_list.append({
                'result_id': result.Id,
                'created': result.Created,
            })
        cache.set("latest:%s" % limit, result_list, timeout=60)

    return render_template('latest.html', listing=result_list)


def index():
    "Index. Renders HTML."

    appraisal_count = cache.get("latest:count")
    if not appraisal_count:
        q = Appraisals.query
        q = q.filter_by()  # NOQA
        appraisal_count = q.count()

        cache.set("latest:count", appraisal_count, timeout=60)

    return render_template('index.html', appraisal_count=appraisal_count)


def legal():
    return render_template('legal.html')


def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])


@oid.loginhandler
def login():
    # if we are already logged in, go back to were we came from
    if g.user is not None:
        return redirect(url_for('index'))
    if request.method == 'POST':
        openid = request.form.get('openid')
        if openid:
            return oid.try_login(openid)

    return render_template('login.html', next=oid.get_next_url(),
                           error=oid.fetch_error())


@oid.after_login
def create_or_login(resp):
    session['openid'] = resp.identity_url
    user = Users.query.filter_by(OpenId=resp.identity_url).first()
    if user is None:
        user = Users(
            OpenId=session['openid'],
            Options=json.dumps(app.config['USER_DEFAULT_OPTIONS']))
        db.session.add(user)
        db.session.commit()

    flash(u'Successfully signed in')
    g.user = user
    return redirect(oid.get_next_url())


def logout():
    session.pop('openid', None)
    session.pop('options', None)
    flash(u'You have been signed out')
    return redirect(url_for('index'))
