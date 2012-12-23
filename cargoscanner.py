# -*- coding: utf-8 -*-
"""
    An Eve Online Cargo Scanner
"""
import json
import urllib2
import time
import datetime
import xml.etree.ElementTree as ET
import humanize
import locale
import os
import sqlite3

from flask import Flask, request, render_template, url_for, redirect
from flask.ext.cache import Cache

# configuration
DEBUG = True
TYPES = json.loads(open('data/types.json').read())
USER_AGENT = 'CargoScanner/1.0 +http://sudorandom.com/cargoscanner'
SCAN_DB = 'data/scans.db'
CACHE_TYPE = 'memcached'
CACHE_KEY_PREFIX = 'cargoscanner'
CACHE_MEMCACHED_SERVERS = ['127.0.0.1:11211']
CACHE_DEFAULT_TIMEOUT = 10 * 60
TEMPLATE = 'default'

cache = Cache()
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_pyfile('application.cfg', silent=True)
locale.setlocale(locale.LC_ALL, 'en_US')
if not os.path.exists(app.config['SCAN_DB']):
    conn = sqlite3.connect(app.config['SCAN_DB'])
    with conn:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE Scans(Id INTEGER PRIMARY KEY,
                                          Data TEXT,
                                          Created INTEGER,
                                          SellValue REAL,
                                          BuyValue REAL)
        """)
        conn.commit()
try:
    os.makedirs('data/scans')
except OSError:
    pass
cache.init_app(app)


# EveType(type_id, count, props)
class EveType(object):
    def __init__(self, type_id, count, props=None, pricing_info=None):
        self.type_id = type_id
        self.count = count
        self.props = props or {}
        self.pricing_info = pricing_info or {}

    def representative_value(self):
        if not self.pricing_info:
            return 0
        sell_price = self.pricing_info.get('totals', {}).get('sell', 0)
        buy_price = self.pricing_info.get('totals', {}).get('buy', 0)
        return max(sell_price, buy_price)

    def is_market_item(self):
        return self.props.get('market', False) == True

    def to_dict(self):
        return {
            'typeID': self.type_id,
            'count': self.count,
            'volume': self.props.get('volume'),
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
                'volume': d.get('volume')
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


def memcache_type_key(typeId):
    return "prices:%s" % typeId


def get_cached_values(eve_types):
    "Get Cached values given the eve_types"
    found = {}
    for eve_type in eve_types:
        key = memcache_type_key(eve_type.type_id)
        obj = cache.get(key)
        if obj:
            found[eve_type.type_id] = obj
        else:
            app.logger.warning("Cache Miss. type_id: %s, %s", eve_type.type_id, key)
    return found


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
    typeids = ["typeid=" + str(x.type_id) for x in eve_types]
    # Forge (for jita): 10000002
    # Metropolis (for hek): 10000042
    # Heimatar (for rens): 10000030
    # Sinq Laison region (for dodixie): 10000032
    # Domain (for amarr): 10000043
    regions = ['regionlimit=10000002', 'regionlimit=10000042',
        'regionlimit=10000030', 'regionlimit=10000032', 'regionlimit=10000043']
    query_str = '&'.join(regions + typeids)
    url = "http://api.eve-central.com/api/marketstat?%s" % query_str
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

            # Cache for up to 10 hours
            cache.set(memcache_type_key(k), v, timeout=10 * 60 * 60)
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

            # Cache for up to 10 hours
            cache.set(memcache_type_key(typeId), prices, timeout=10 * 60 * 60)
        return market_prices
    except urllib2.HTTPError:
        return {}


def save_scan(scan_result):
    conn = sqlite3.connect(app.config['SCAN_DB'])
    with conn:
        cur = conn.cursor()
        data = json.dumps(scan_result, indent=2)
        cur.execute("""INSERT INTO Scans(Data, Created, BuyValue, SellValue)
                       VALUES (?, strftime('%s','now'), ?, ?);""",
                       (data, scan_result['totals']['buy'],
                        scan_result['totals']['sell']))
        conn.commit()
        return cur.lastrowid


def load_scan(scan_id):
    try:
        int(scan_id)
    except:
        return
    conn = sqlite3.connect(app.config['SCAN_DB'])
    with conn:
        cur = conn.cursor()
        cur.execute("SELECT Data From Scans WHERE id=?;", (scan_id, ))
        conn.commit()
        scan_data = cur.fetchone()
        if scan_data:
            return json.loads(scan_data[0])


def parse_scan_items(scan_result):
    """
        Takes a scan result and returns:
            {'name': {details}, ...}, ['bad line']
    """
    lines = scan_result.splitlines()
    lines = [line.strip() for line in scan_result.splitlines() if line.strip()]

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

        # aiming for the format "2 Cargo Scanner II" and "2x Cargo Scanner II"
        try:
            count, name = fmt_line.split(' ', 1)
            count = int(count.replace('x', '').strip())
            if _add_type(name.strip(), count):
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
        if '[' in fmt_line and ']' in fmt_line and fmt_line.count(",") > 0:
            item, _ = fmt_line.strip('[').split(',', 1)
            if _add_type(item.strip(), 1):
                continue

        # aiming for format "PERSON'S NAME\tShipType\tdistance"
        if fmt_line.count("\t") == 2:
            _, item, _ = fmt_line.split("\t", 2)
            if _add_type(item.strip(), 1):
                continue

        # aiming for format "Item Name\tCount..."
        try:
            if fmt_line.count("\t") > 1:
                item, count, _ = fmt_line.split("\t", 2)
                if _add_type(item.strip(), int(count.strip())):
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
            zeroed_price = {'avg': 0, 'min': 0, 'max': 0, 'price': 0}
            price_info = {
                'buy': zeroed_price.copy(),
                'sell': zeroed_price.copy(),
                'all': zeroed_price.copy(),
            }
            invalid_items[eve_type.type_id] = price_info
    return invalid_items


def get_componentized_values(eve_types):
    componentized_items = {}
    for eve_type in eve_types:
        if 'components' in eve_type.props:
            component_types = [EveType(c['materialTypeID'], c['quantity'])
                for c in eve_type.props['components']]

            populate_market_values(component_types, methods=[get_cached_values,
                get_market_values, get_market_values_2])
            zeroed_price = {'avg': 0, 'min': 0, 'max': 0, 'price': 0}
            complete_price_data = {
                'buy': zeroed_price.copy(),
                'sell': zeroed_price.copy(),
                'all': zeroed_price.copy(),
            }
            for component in component_types:
                for market_type in ['buy', 'sell', 'all']:
                    for stat in ['avg', 'min', 'max', 'price']:
                        complete_price_data[market_type][stat] += \
                            component.pricing_info[market_type][stat] * component.count
            componentized_items[eve_type.type_id] = complete_price_data
            # Cache for up to 10 hours
            cache.set(memcache_type_key(eve_type.type_id), complete_price_data,
                timeout=10 * 60 * 60)

    return componentized_items


def populate_market_values(eve_types, methods=None):
    unpopulated_types = list(eve_types)
    if methods is None:
        methods = [get_invalid_values, get_cached_values,
            get_componentized_values, get_market_values, get_market_values_2]
    for pricing_method in methods:
        if len(unpopulated_types) == 0:
            break
        # returns a dict with {type_id: pricing_info}
        prices = pricing_method(unpopulated_types)
        app.logger.debug("Found %s/%s items using method: %s", len(prices),
            len(unpopulated_types), pricing_method)
        new_unpopulated_types = []
        for eve_type in unpopulated_types:
            if eve_type.type_id in prices:
                pdata = prices[eve_type.type_id]
                pdata['totals'] = {
                    'volume': eve_type.props.get('volume', 0) * eve_type.count
                }
                for total_key in ['sell', 'buy', 'all']:
                    _total = pdata[total_key]['price'] * eve_type.count
                    pdata['totals'][total_key] = _total
                eve_type.pricing_info = pdata
            else:
                new_unpopulated_types.append(eve_type)
        unpopulated_types = new_unpopulated_types
    return eve_types


@app.route('/estimate', methods=['POST'])
def estimate_cost():
    "Estimate Cost of scan result given by POST[SCAN_RESULT]. Renders HTML"
    raw_scan = request.form.get('scan_result', '')
    eve_types, bad_lines = parse_scan_items(raw_scan)

    # Populate types with pricing data
    populate_market_values(eve_types)

    # calculate the totals
    totals = {'sell': 0, 'buy': 0, 'all': 0, 'volume': 0}
    for t in eve_types:
        for total_key in ['sell', 'buy', 'all', 'volume']:
            totals[total_key] += t.pricing_info['totals'][total_key]

    sorted_eve_types = sorted(eve_types, key=lambda k: -k.representative_value())
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
        scan_id = save_scan(scan_results)
        scan_results['scan_id'] = scan_id
    return render_template('scan_results.html', scan_results=scan_results,
        from_igb=is_from_igb(), full_page=request.form.get('load_full'))


@app.route('/estimate/<int:scan_id>', methods=['GET'])
def display_scan(scan_id):
    scan_results = load_scan(scan_id)
    error = None
    status = 200
    if scan_results:
        scan_results['scan_id'] = scan_id
    else:
        error = "Scan Not Found"
        status = 404
    return render_template('scan_results.html', scan_results=scan_results,
     error=error, from_igb=is_from_igb(), full_page=True), status


@app.route('/latest/', defaults={'limit': 20})
@app.route('/latest/limit/<int:limit>')
# @cache.cached(timeout=60)
def latest(limit):
    print "EXECUTED THIS"
    if limit > 1000:
        return redirect(url_for('latest', limit=1000))
    conn = sqlite3.connect('data/scans.db')
    results = []
    with conn:
        cur = conn.cursor()
        cur.execute("""SELECT Id, Created, BuyValue, SellValue FROM Scans
                       ORDER BY Created DESC, Id DESC
                       LIMIT ?;""", (limit, ))
        for result in cur.fetchall():
            _id, _timestamp, buy_value, sell_value = result
            results.append({
                    'scan_id': _id,
                    'created': _timestamp,
                    'buy_value': buy_value,
                    'sell_value': sell_value,
                })
    return render_template('latest.html', listing=results)


@app.route('/', methods=['GET', 'POST'])
def index():
    "Index. Renders HTML."
    return render_template('index.html', from_igb=is_from_igb())


if __name__ == '__main__':
    app.run()
