import locale
import datetime
import humanize

from . import app


@app.template_filter('format_isk')
def format_isk(value):
    try:
        return "%s ISK" % locale.format("%.2f", value, grouping=True)
    except:
        return ""


@app.template_filter('format_isk_human')
def format_isk_human(value):
    if value is None:
        return ""
    try:
        return "%s ISK" % humanize.intword(value, format='%.2f')
    except:
        return str(value)


@app.template_filter('format_volume')
def format_volume(value):
    try:
        if value == 0:
            return "0m<sup>3</sup>"
        if value < 0.01:
            return "%.4fm<sup>3</sup>" % value
        if value < 1:
            return "%.2fm<sup>3</sup>" % value
        return "%sm<sup>3</sup>" % humanize.intcomma(int(value))
    except:
        return "unknown m<sup>3</sup>"


@app.template_filter('relative_time')
def relative_time(past):
    try:
        return humanize.naturaltime(datetime.datetime.fromtimestamp(past))
    except:
        return ""


@app.template_filter('bpc_count')
def bpc_count(bad_lines):
    c = 0
    for line in bad_lines:
        if '(copy)' in line.lower():
            c += 1
    return c
