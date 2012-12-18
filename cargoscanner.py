# -*- coding: utf-8 -*-
"""
    An Eve Online Cargo Scanner
"""
import memcache
import json
import urllib2
import time
import datetime
import xml.etree.ElementTree as ET
import humanize
import locale
import os

from flask import Flask, request, render_template, _app_ctx_stack

# configuration
DEBUG = True
MEMCACHE_PREFIX = 'cargoscanner'
TYPES = json.loads(open('data/types.json').read())
USER_AGENT = 'CargoScanner/1.0 +http://sudorandom.com/cargoscanner'

app = Flask(__name__)
app.config.from_object(__name__)
locale.setlocale(locale.LC_ALL, 'en_US')
try:
    os.makedirs('data/scans')
except OSError:
    pass


@app.template_filter('format_isk')
def format_isk(value):
    return "%s ISK" % locale.format("%.2f", value, grouping=True)


@app.template_filter('format_isk_human')
def format_isk_human(value):
    return "%s ISK" % humanize.intword(value, format='%.2f')


@app.template_filter('relative_time')
def relative_time(past):
    return humanize.naturaltime(datetime.datetime.fromtimestamp(past))


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
            print("Cache Miss. typeId: %s, %s" % (typeId, key))
            not_found.append(typeId)
    return found, not_found


def set_cache_value(typeId, value):
    "Set cache value."
    mc = get_cache()
    key = memcache_type_key(typeId)
    # Cache for up to 2 hours
    mc.set(key, value, time=2 * 60 * 60)


def get_market_values(typeIds):
    """
        Takes list of typeIds. Returns dict of pricing details with typeId as
        the key. Calls out to the eve-central.
    """
    if len(typeIds) == 0:
        return {}
    typeIds_str = ','.join(str(x) for x in typeIds)
    url = "http://api.eve-central.com/api/marketstat?typeid=%s" % typeIds_str
    request = urllib2.Request(url)
    request.add_header('User-Agent', app.config['USER_AGENT'])
    response = urllib2.build_opener().open(request).read()
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
    request = urllib2.Request(url)
    request.add_header('User-Agent', app.config['USER_AGENT'])
    response = json.loads(urllib2.build_opener().open(request).read())

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

    for typeId, prices in market_prices.iteritems():
        set_cache_value(typeId, prices)
    return market_prices


def get_current_scan_id():
    scan_id_file = "data/current_scan_id.dat"
    if not os.path.exists(scan_id_file):
        with open(scan_id_file, 'w') as f:
            f.write('1')
        return 0

    with open(scan_id_file, 'r+') as f:
        scan_id = int(f.read())
        f.seek(0)
        f.write(str(scan_id + 1))
        return scan_id


def save_scan(scan_id, scan_result):
    with open("data/scans/%s" % scan_id, 'w') as f:
        f.write(json.dumps(scan_result))


def load_scan(scan_id):
    try:
        int(scan_id)
    except:
        return
    scan_file = "data/scans/%s" % scan_id
    if os.path.exists(scan_file):
        with open(scan_file) as f:
            return json.loads(f.read())


def parse_scan_items(scan_result):
    """
        Takes a scan result and returns:
            {'name': {details}, ...}, [(2, 'bad name')]
    """
    lines = scan_result.splitlines()
    lines = [line.replace('\t', '').strip() \
                for line in scan_result.splitlines() if line.strip()]

    results = {}
    for line in lines:
        try:
            count, name = line.split(' ', 1)
            count = int(count.strip())
        except ValueError:
            count, name = 1, line
        name = name.lower().strip()
        # Copies are not found through this database at the moment...
        name = name.replace(' (original)', '')
        if name in results:
            results[name] += count
        else:
            results[name] = count

    typed_results = {}
    bad_lines = []
    for name, count in results.iteritems():
        details = app.config['TYPES'].get(name)
        if details:
            typed_results[details['typeID']] = \
                dict(details.items() + [('count', count)])
        else:
            bad_lines.append((count, name))

    return typed_results, bad_lines


def is_from_igb():
    return request.headers.get('User-Agent', '').find("EVE-IGB") != -1


@app.route('/estimate', methods=['POST'])
def estimate_cost():
    "Estimate Cost of scan result given by POST[SCAN_RESULT]. Renders HTML"
    raw_scan = request.form.get('scan_result', '')
    from_igb = is_from_igb()
    results, bad_lines = parse_scan_items(raw_scan)
    found, not_found = get_cached_values(results.keys())
    try:
        fresh_data = get_market_values(not_found)
    except:
        print "ERROR: Could not get price data from Eve-Central: %s" % not_found
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
        'from_igb': from_igb,
        'totals': totals,
        'bad_line_items': bad_lines,
        'line_items': sorted_line_items,
        'created': time.time(),
        'raw_scan': raw_scan,
    }
    if len(sorted_line_items) > 0:
        scan_id = get_current_scan_id()
        scan_results['scan_id'] = scan_id
        save_scan(scan_id, scan_results)
    return display_scan_result(scan_results,
        full_page=request.form.get('load_full'))


@app.route('/estimate/<scan_id>', methods=['GET'])
def display_scan(scan_id):
    scan_results = load_scan(scan_id)
    if scan_results:
        return display_scan_result(scan_results, full_page=True)
    else:
        return render_template('index.html', error="Scan Not Found")


def display_scan_result(scan_results, full_page=False):
    if full_page:
        return render_template('index.html', scan_results=scan_results,
            from_igb=is_from_igb())
    else:
        return render_template('scan_results.html', scan_results=scan_results,
            from_igb=is_from_igb())


@app.route('/', methods=['GET', 'POST'])
def index():
    "Index. Renders HTML."
    return render_template('index.html')


if __name__ == '__main__':
    app.run()
