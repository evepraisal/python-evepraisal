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

from helpers import login_required, save_result, load_result, is_from_igb
from parser import parse_paste_items
from estimate import populate_market_values
from models import Scans, Users
from . import app, db, cache, oid


def estimate_cost():
    """ Estimate Cost of pasted stuff result given by POST[raw_paste].
        Renders HTML """
    raw_paste = request.form.get('raw_paste', '')
    solar_system = request.form.get('market', '30000142')

    if solar_system not in app.config['VALID_SOLAR_SYSTEMS'].keys():
        abort(400)

    eve_types, bad_lines = parse_paste_items(raw_paste)

    # Populate types with pricing data
    populate_market_values(eve_types, options={'solarsystem_id': solar_system})

    # calculate the totals
    totals = {'sell': 0, 'buy': 0, 'all': 0, 'volume': 0}
    for t in eve_types:
        for total_key in ['sell', 'buy', 'all', 'volume']:
            totals[total_key] += t.pricing_info['totals'][total_key]

    sorted_eve_types = sorted(
        eve_types, key=lambda k: -k.representative_value())
    displayable_line_items = []
    for eve_type in sorted_eve_types:
        displayable_line_items.append(eve_type.to_dict())
    results = {
        'from_igb': is_from_igb(),
        'totals': totals,
        'bad_line_items': bad_lines,
        'line_items': displayable_line_items,
        'created': time.time(),
        'raw_paste': raw_paste,
        'solar_system': solar_system,
        'solar_system_name': app.config['VALID_SOLAR_SYSTEMS'].get(
            solar_system, 'UNKNOWN'),
    }
    if len(sorted_eve_types) > 0:
        if session['options'].get('share'):
            result_id = save_result(results, public=True)
            results['result_id'] = result_id
        else:
            result_id = save_result(results, public=False)
    return render_template(
        'results.html', results=results, from_igb=is_from_igb(),
        full_page=request.form.get('load_full'))


def display_result(result_id):
    results = load_result(result_id)
    if results:
        results['result_id'] = result_id
        return render_template(
            'results.html', results=results, from_igb=is_from_igb(),
            full_page=True)
    else:
        flash('Resource Not Found', 'error')
        return render_template(
            'index.html', from_igb=is_from_igb(), full_page=True), 404


@login_required
def options():
    if request.method == 'POST':
        print request.form
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
    q = Scans.query
    q = q.filter(Scans.UserId == g.user.Id)
    q = q.order_by(desc(Scans.Created), desc(Scans.Id))
    q = q.limit(100)
    results = q.all()

    result_list = []
    for result in results:
        result_list.append({
            'result_id': result.Id,
            'created': result.Created,
            'buy_value': result.BuyValue,
            'sell_value': result.SellValue,
        })

    return render_template('history.html', listing=result_list)


def latest(limit):
    if limit > 1000:
        return redirect(url_for('latest', limit=1000))

    result_list = cache.get("latest:%s" % limit)
    if not result_list:
        q = Scans.query
        q = q.filter_by(Public=True)  # NOQA
        q = q.order_by(desc(Scans.Created), desc(Scans.Id))
        q = q.limit(limit)
        results = q.all()

        result_list = []
        for result in results:
            result_list.append({
                'result_id': result.Id,
                'created': result.Created,
                'buy_value': result.BuyValue,
                'sell_value': result.SellValue,
            })
        cache.set("latest:%s" % limit, result_list, timeout=60)

    return render_template('latest.html', listing=result_list)


def index():
    "Index. Renders HTML."
    return render_template('index.html', from_igb=is_from_igb())


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
        print "CREATE USER"
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
