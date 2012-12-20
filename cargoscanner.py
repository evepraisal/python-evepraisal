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


# EveType(type_id, count, props)
class EveType(object):
    def __init__(self, type_id, count, props=None, pricing_info=None):
        self.type_id = type_id
        self.count = count
        self.props = props or {}
        self.pricing_info = pricing_info or {}

    def is_market_item(self):
        return self.props.get('market', False) == True

    def to_dict(self):
        return {
            'typeID': self.type_id,
            'count': self.count,
            'typeName': self.props.get('typeName'),
            'groupID': self.props.get('groupID'),
            'totals': self.pricing_info.get('totals'),
            'sell': self.pricing_info.get('sell'),
            'buy': self.pricing_info.get('buy'),
            'all': self.pricing_info.get('all'),
        }

    @classmethod
    def from_dict(self, cls, d):
        return cls(d['typeID'], d['count'],
            {
                'typeName': d.get('typeName'),
                'groupID': d.get('groupID'),
            },
            {
                'totals': d.get('totals'),
                'sell': d.get('sell'),
                'buy': d.get('buy'),
                'all': d.get('all'),
            }
        )


@app.template_filter('format_isk')
def format_isk(value):
    try:
        return "%s ISK" % locale.format("%.2f", value, grouping=True)
    except:
        return ""


@app.template_filter('format_isk_human')
def format_isk_human(value):
    try:
        return "%s ISK" % humanize.intword(value, format='%.2f')
    except:
        return ""


@app.template_filter('format_volume')
def format_volume(value):
    try:
        return humanize.intcomma(value)
    except:
        return ""


@app.template_filter('relative_time')
def relative_time(past):
    try:
        return humanize.naturaltime(datetime.datetime.fromtimestamp(past))
    except:
        return ""


def memcache_type_key(typeId):
    return "%s:prices:%s" % (app.config['MEMCACHE_PREFIX'], typeId)


def get_cache():
    "Returns memcache client instance"
    top = _app_ctx_stack.top
    if not hasattr(top, 'memcache'):
        top.memcache = memcache.Client(['127.0.0.1:11211'], debug=0)
    return top.memcache


def get_cached_values(eve_types):
    "Get Cached values given the eve_types"
    mc = get_cache()
    found = {}
    for eve_type in eve_types:
        key = memcache_type_key(eve_type.type_id)
        obj = mc.get(key)
        if obj:
            found[eve_type.type_id] = obj
        else:
            app.logger.warning("Cache Miss. type_id: %s, %s", eve_type.type_id, key)
    return found


def set_cache_value(typeId, value):
    "Set cache value."
    mc = get_cache()
    key = memcache_type_key(typeId)
    # Cache for up to 2 hours
    mc.set(key, value, time=10 * 60 * 60)


def get_market_values(eve_types):
    """
        Takes list of typeIds. Returns dict of pricing details with typeId as
        the key. Calls out to the eve-central.

        Example Return Value:
        {
            21574:{
             'all': {'avg': 254.83, 'min': 254.83, 'max': 254.83, 'price': 254.83},
             'buy': {'avg': 5434414.43, 'min': 5434414.43, 'max': 5434414.43, 'price': 5434414.43},
             'sell': {'avg': 10552957.04, 'min': 10552957.04, 'max': 10552957.04, 'price': 10552957.04}
        }
    """
    if len(eve_types) == 0:
        return {}
    typeIds_str = ','.join(str(x.type_id) for x in eve_types)
    url = "http://api.eve-central.com/api/marketstat?typeid=%s" % typeIds_str
    try:
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
                for stat in marketstat.find(stat_type):
                    props[stat.tag] = float(stat.text)
                v[stat_type] = props
            v['all']['price'] = v['all']['avg']
            v['buy']['price'] = v['buy']['max']
            v['sell']['price'] = v['sell']['min']
            market_prices[k] = v
            set_cache_value(k, v)
        return market_prices
    except urllib2.HTTPError:
        return {}


def get_market_values_2(eve_types):
    """
        Takes list of typeIds. Returns dict of pricing details with typeId as
        the key. Calls out to the eve-marketdata.
        Example Return Value:
        {
            21574:{
             'all': {'avg': 254.83, 'min': 254.83, 'max': 254.83, 'price': 254.83},
             'buy': {'avg': 5434414.43, 'min': 5434414.43, 'max': 5434414.43, 'price': 5434414.43},
             'sell': {'avg': 10552957.04, 'min': 10552957.04, 'max': 10552957.04, 'price': 10552957.04}
        }
    """
    if len(eve_types) == 0:
        return {}
    typeIds_str = ','.join(str(x.type_id) for x in eve_types)
    url = "http://api.eve-marketdata.com/api/item_prices2.json?char_name=magerawr&type_ids=%s&buysell=a" % typeIds_str
    try:
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
                price = float(row['price'])
                market_prices[k]['sell'] = {'avg': price, 'min': price, 'max': price}
            elif row['buysell'] == 'b':
                price = float(row['price'])
                market_prices[k]['buy'] = {'avg': price, 'min': price, 'max': price}

        for typeId, prices in market_prices.iteritems():
            avg = (prices['sell']['avg'] + prices['buy']['avg']) / 2
            market_prices[typeId]['all'] = {'avg': avg, 'min': avg, 'max': avg, 'price': avg}
            market_prices[typeId]['buy']['price'] = market_prices[typeId]['buy']['max']
            market_prices[typeId]['sell']['price'] = market_prices[typeId]['sell']['min']
            set_cache_value(typeId, prices)
        return market_prices
    except urllib2.HTTPError:
        return {}


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
        f.write(json.dumps(scan_result, indent=2))


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
    bad_lines = []

    def _add_type(name, count):
        details = app.config['TYPES'].get(name)
        if not details:
            return False
        type_id = details['typeID']
        if type_id in results:
            results[type_id].count += count
        else:
            results[type_id] = EveType(type_id, count, details.copy())
        return True

    for line in lines:
        fmt_line = line.lower().replace(' (original)', '')

        # aiming for the format "Cargo Scanner II"
        if _add_type(fmt_line, 1):
            continue

        # aiming for the format "2 Cargo Scanner II"
        try:
            count, name = fmt_line.split(' ', 1)
            count = int(count.strip())
            if _add_type(name, count):
                continue
        except ValueError:
            pass

        # aiming for the format
        # "800mm Repeating Artillery II, Republic Fleet EMP L"
        if ',' in fmt_line:
            item, item2 = fmt_line.rsplit(',', 1)
            _add_type(item2.strip(), 1)
            if _add_type(item.strip(), 1):
                continue

        # aiming for the format "Hornet x5"
        try:
            if 'x' in fmt_line:
                item, count = fmt_line.rsplit('x', 1)
                if _add_type(item.strip(), int(count.strip())):
                    continue
        except ValueError:
            pass

        # aiming for the format "[panther, my pimp panther]"
        try:
            if '[' in fmt_line and ']' in fmt_line:
                item, _ = fmt_line.strip('[').split(',', 1)
                if _add_type(item.strip(), 1):
                    continue
        except ValueError:
            pass

        bad_lines.append(line)

    return results.values(), bad_lines


def is_from_igb():
    return request.headers.get('User-Agent', '').find("EVE-IGB") != -1


def get_invalid_values(eve_types):
    invalid_items = {}
    for eve_type in eve_types:
        if eve_type.props.get('market') == False:
            price_info = {}
            zeroed_price = {'avg': 0, 'min': 0, 'max': 0, 'price': 0}
            price_info['buy'] = zeroed_price
            price_info['sell'] = zeroed_price
            price_info['all'] = zeroed_price
            invalid_items[eve_type.type_id] = price_info
    return invalid_items


@app.route('/estimate', methods=['POST'])
def estimate_cost():
    "Estimate Cost of scan result given by POST[SCAN_RESULT]. Renders HTML"
    raw_scan = request.form.get('scan_result', '')
    eve_types, bad_lines = parse_scan_items(raw_scan)

    # Populate types with pricing data
    unpopulated_types = list(eve_types)
    totals = {'sell': 0, 'buy': 0, 'all': 0}
    for pricing_method in [get_invalid_values, get_cached_values,
            get_market_values, get_market_values_2]:
        if len(unpopulated_types) == 0:
            break
        # returns a dict with type_id: pricing_info
        prices = pricing_method(unpopulated_types)
        app.logger.debug("Found %s/%s items using method: %s", len(prices),
            len(unpopulated_types), pricing_method)
        new_unpopulated_types = []
        for eve_type in unpopulated_types:
            if eve_type.type_id in prices:
                pdata = prices[eve_type.type_id]
                pdata['totals'] = {}
                for total_key in ['sell', 'buy', 'all']:
                    _total = pdata[total_key]['price'] * eve_type.count
                    pdata['totals'][total_key] = _total
                    totals[total_key] += _total
                eve_type.pricing_info = pdata
            else:
                new_unpopulated_types.append(eve_type)
        unpopulated_types = new_unpopulated_types

    sorted_eve_types = sorted(eve_types,
        key=lambda k: -k.pricing_info.get('totals', {}).get('all', 0))
    displayable_line_items = []
    for eve_type in sorted_eve_types:
        displayable_line_items.append(eve_type.to_dict())
    scan_results = {
        'from_igb': is_from_igb(),
        'totals': totals,
        'bad_line_items': bad_lines,
        'line_items': displayable_line_items,
        'created': time.time(),
        'raw_scan': raw_scan,
    }
    if len(sorted_eve_types) > 0:
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
        return render_template('index.html', error="Scan Not Found",
            from_igb=is_from_igb())


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
    return render_template('index.html', from_igb=is_from_igb())


if __name__ == '__main__':
    app.run()
