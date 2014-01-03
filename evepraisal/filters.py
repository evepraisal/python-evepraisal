import time
import math
from datetime import timedelta
from babel.dates import format_timedelta
from flask import request

from . import app
from models import get_type_by_name


@app.context_processor
def utility_processor():
    def is_from_igb():
        return 'EVE-IGB' in request.headers.get('User-Agent', '')
    return dict(is_from_igb=is_from_igb)


@app.template_filter('market_name')
def get_market_name(market_id):
    return app.config['VALID_SOLAR_SYSTEMS'].get(str(market_id), 'UNKNOWN')


@app.template_filter('type_details')
def type_details(type_name):
    return get_type_by_name(type_name) or {'typeID': 1, 'typeName': type_name}


@app.template_filter('make_price_table')
def make_price_table(prices):
    return dict(prices)


# Adapted from http://stackoverflow.com/a/3155023/74375
def millify(n, fmt="{:,.2f}"):
    millnames = ['', 'Thousand', 'Million', 'Billion', 'Trillion',
                 'Quadrillion', 'Quintillion', 'Sextillion', 'Septillion',
                 'Octillion', 'Nonillion', 'Decillion']
    millidx = max(0, min(len(millnames) - 1,
                         int(math.floor(math.log10(abs(n)) / 3.0))))
    num = n / 10 ** (3 * millidx)
    return (fmt + ' {}').format(num,
                                millnames[millidx])


@app.template_filter('comma_separated_int')
def comma_separated_int(value):
    try:
        return "{:,}".format(value)
    except Exception:
        return ""


@app.template_filter('format_isk')
def format_isk(value):
    try:
        return "{:,.2f}".format(value)
    except Exception:
        return ""


@app.template_filter('format_isk_human')
def format_isk_human(value):
    if value is None:
        return ""
    if value == 0:
        return "0 ISK"

    return "%s ISK" % millify(value)


@app.template_filter('format_volume')
def format_volume(value):
    try:
        if value == 0:
            return "0"
        if value < 0.01:
            return "%.4f" % value
        if value < 1:
            return "%.2f" % value
        return "{:,.2f}".format(value)
    except Exception:
        return "unknown"


@app.template_filter('relative_time')
def relative_time(past):
    now = time.time()
    delta_seconds = now-past
    if abs(delta_seconds) < 1:
        return 'just now'
    postfix = ' ago'
    if past > now:
        postfix = ' in the future'
    try:
        delta = timedelta(seconds=delta_seconds)
        return format_timedelta(delta, locale='en_US') + postfix
    except Exception:
        return ''


@app.template_filter('bpc_count')
def bpc_count(bad_lines):
    c = 0
    for line in bad_lines:
        if '(copy)' in line.lower():
            c += 1
    return c
