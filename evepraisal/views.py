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
import evepaste

from helpers import login_required
from estimate import get_market_prices
from models import Appraisals, Users, appraisal_count
from parser import parse
from . import app, db, cache, oid


def estimate_cost():
    """ Estimate Cost of pasted stuff result given by POST[raw_paste].
        Renders HTML """
    raw_paste = request.form.get('raw_paste', '')
    solar_system = request.form.get('market', '30000142')

    if solar_system not in app.config['VALID_SOLAR_SYSTEMS'].keys():
        abort(400)

    encoded_raw_paste = raw_paste.encode('utf-8')
    try:
        parse_results = parse(encoded_raw_paste)
    except evepaste.Unparsable as ex:
        if encoded_raw_paste:
            app.logger.warning("User input invalid data: %s",
                               encoded_raw_paste)
        return render_template(
            'error.html', error='Error when parsing input: ' + str(ex))

    # Populate types with pricing data
    prices = get_market_prices(list(parse_results['unique_items']),
                               options={'solarsystem_id': solar_system})

    appraisal = Appraisals(Created=int(time.time()),
                           RawInput=raw_paste,
                           Kind=parse_results['representative_kind'],
                           Prices=prices,
                           Parsed=parse_results['results'],
                           ParsedVersion=1,
                           BadLines=parse_results['bad_lines'],
                           Market=solar_system,
                           Public=bool(session['options'].get('share')),
                           UserId=g.user.Id if g.user else None)
    db.session.add(appraisal)
    db.session.commit()

    return render_template('results.html',
                           appraisal=appraisal)


def display_result(result_id):
    page = cache.get('appraisal:%s' % result_id)
    if page:
        return page

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

    page = render_template('results.html',
                           appraisal=appraisal,
                           full_page=True)
    if appraisal.Public:
        try:
            cache.set('appraisal:%s' % result_id, page, timeout=30)
        except Exception:
            pass
    return page


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
    q = q.order_by(desc(Appraisals.Created))
    q = q.limit(100)
    appraisals = q.all()

    return render_template('history.html', appraisals=appraisals)


@cache.memoize(timeout=30)
def latest():
    q = Appraisals.query
    q = q.filter_by(Public=True)  # NOQA
    q = q.order_by(desc(Appraisals.Created))
    q = q.limit(200)
    appraisals = q.all()
    return render_template('latest.html', appraisals=appraisals)


def index():
    "Index. Renders HTML."

    count = cache.get("latest:count")
    if not count:
        count = appraisal_count()
        cache.set("latest:count", count, timeout=60)

    return render_template('index.html', appraisal_count=count)


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
