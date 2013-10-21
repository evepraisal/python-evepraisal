import time
import math
from datetime import timedelta
from babel.dates import format_timedelta

from . import app


# Adopted from http://stackoverflow.com/a/3155023/74375
def millify(n, format="{:,.2f}"):
    millnames = ['', 'Thousand', 'Million', 'Billion', 'Trillion',
                 'Quadrillion', 'Quintillion', 'Sextillion', 'Septillion',
                 'Octillion', 'Nonillion', 'Decillion']
    millidx = max(0, min(len(millnames) - 1,
                         int(math.floor(math.log10(abs(n)) / 3.0))))
    num = n / 10 ** (3 * millidx)
    return (format + ' {}').format(num,
                                   millnames[millidx])


@app.template_filter('format_isk')
def format_isk(value):
    try:
        return "{:,.2f}".format(value)
    except:
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
            return "0m<sup>3</sup>"
        if value < 0.01:
            return "%.4fm<sup>3</sup>" % value
        if value < 1:
            return "%.2fm<sup>3</sup>" % value
        return "{:,.2f}m<sup>3</sup>".format(value)
    except:
        return "unknown m<sup>3</sup>"


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
    except:
        return ''


@app.template_filter('bpc_count')
def bpc_count(bad_lines):
    c = 0
    for line in bad_lines:
        if '(copy)' in line.lower():
            c += 1
    return c
