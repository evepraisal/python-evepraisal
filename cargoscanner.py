# -*- coding: utf-8 -*-
"""
    An Eve Online Cargo Scanner
"""
import memcache
import json
import urllib2
import xml.etree.ElementTree as ET
import humanize
import locale

from flask import Flask, request, render_template, _app_ctx_stack

# configuration
DEBUG = True
MEMCACHE_PREFIX = 'cargoscanner'
TYPES = json.loads(open('data/types.json').read())

app = Flask(__name__)
app.config.from_object(__name__)
locale.setlocale(locale.LC_ALL, 'en_US')


@app.template_filter('format_isk')
def format_isk(value):
    return "%s ISK" % locale.format("%.2f", value, grouping=True)


@app.template_filter('format_isk_human')
def format_isk_human(value):
    return "%s ISK" % humanize.intword(value, format='%.2f')


def memcache_type_key(typeId):
    return "%s:prices:%s" % (app.config['MEMCACHE_PREFIX'], typeId)


def get_cache():
    "Returns memcache client instance"
    top = _app_ctx_stack.top
    if not hasattr(top, 'memcache'):
        top.memcache = memcache.Client(['127.0.0.1:11211'], debug=0)
    return top.memcache


def get_cached_values(typeIds):
    "Get Cached values given the typeId"
    mc = get_cache()
    found = {}
    not_found = []
    for typeId in typeIds:
        key = memcache_type_key(typeId)
        obj = mc.get(key)
        if obj:
            found[typeId] = obj
        else:
            print("Cache Miss. typeId: %s" % typeId)
            not_found.append(typeId)
    return found, not_found


def set_cache_value(typeId, value):
    "Set cache value."
    mc = get_cache()
    key = memcache_type_key(typeId)
    mc.set(key, value)


def get_market_values(typeIds):
    """
        Takes list of typeIds. Returns dict of pricing details with typeId as
        the key. Calls out to the eve-central.
    """
    if len(typeIds) == 0:
        return {}
    typeIds_str = ','.join(str(x) for x in typeIds)
    url = "http://api.eve-central.com/api/marketstat?typeid=%s" % typeIds_str
    response = urllib2.urlopen(url).read()
    stats = ET.fromstring(response).findall("./marketstat/type")
    market_prices = {}
    for marketstat in stats:
        k = int(marketstat.attrib.get('id'))
        v = {}
        for stat_type in ['sell', 'buy', 'all']:
            props = {}
            for stat in marketstat.find('%s' % stat_type):
                props[stat.tag] = float(stat.text)
            v[stat_type] = props
        set_cache_value(k, v)
        market_prices[k] = v
    return market_prices


def get_market_values_2(typeIds):
    """
        Takes list of typeIds. Returns dict of pricing details with typeId as
        the key. Calls out to the eve-marketdata.
        Example Return Value:
        {
            21574:{
             'all': {'avg': 254.83},
             'buy': {'avg': 5434414.43},
             'sell': {'avg': 10552957.04}}
        }
    """
    if len(typeIds) == 0:
        return {}
    typeIds_str = ','.join(str(x) for x in typeIds)
    url = "http://api.eve-marketdata.com/api/item_prices2.json?char_name=magerawr&type_ids=%s&buysell=a" % typeIds_str
    response = json.loads(urllib2.urlopen(url).read())

    market_prices = {}
    for row in response['emd']['result']:
        row = row['row']
        k = int(row['typeID'])
        if k not in market_prices:
            market_prices[k] = {}
        if row['buysell'] == 's':
            market_prices[k]['sell'] = {'avg': float(row['price'])}
        elif row['buysell'] == 'b':
            market_prices[k]['buy'] = {'avg': float(row['price'])}

    for typeId, prices in market_prices.iteritems():
        avg = (prices['buy']['avg'] + prices['buy']['avg']) / 2
        market_prices[typeId]['all'] = {'avg': avg}

    for typeId, prices in prices.iteritems():
        set_cache_value(typeId, prices)
    return market_prices


def parse_scan_items(scan_result):
    "Takes a scan result and returns {'name': {details}, ...} "
    lines = scan_result.splitlines()
    lines = [line.strip() for line in scan_result.splitlines() if line.strip()]

    results = {}
    for line in lines:
        try:
            count, name = line.split(' ', 1)
            count = int(count)
        except ValueError:
            count, name = 1, line
        name = name.lower()
        if name in results:
            results[name] += count
        else:
            results[name] = count

    typed_results = {}
    for name, count in results.iteritems():
        details = app.config['TYPES'].get(name)
        if details:
            typed_results[details['typeID']] = \
                dict(details.items() + [('count', count)])

    return typed_results


@app.route('/estimate', methods=['POST'])
def estimate_cost():
    "Estimate Cost of scan result given by POST[SCAN_RESULT]. Renders HTML"
    results = parse_scan_items(request.form.get('scan_result', ''))
    found, not_found = get_cached_values(results.keys())
    try:
        fresh_data = get_market_values(not_found)
    except:
        fresh_data = get_market_values_2(not_found)
    prices = dict(found.items() + fresh_data.items())
    totals = {'sell': 0, 'buy': 0, 'all': 0}
    for typeId, price_data in prices.iteritems():
        price_data = dict(price_data.items() + results[typeId].items())
        results[typeId] = price_data
        results[typeId]['totals'] = {}
        for total_key in ['sell', 'buy', 'all']:
            _total = price_data[total_key]['avg'] * price_data['count']
            results[typeId]['totals'][total_key] = _total
            totals[total_key] += _total

    sorted_line_items = sorted(results.values(),
        key=lambda k: -k['totals']['all'])
    scan_results = {
        'totals': totals,
        'line_items': sorted_line_items,
    }
    if request.form.get('load_full'):
        return render_template('index.html', scan_results=scan_results)
    else:
        return render_template('scan_results.html', scan_results=scan_results)


@app.route('/', methods=['GET', 'POST'])
def index():
    "Index. Renders HTML."
    return render_template('index.html')


if __name__ == '__main__':
    app.run()
