import urllib2
import json
import xml.etree.ElementTree as ET

from . import app, cache
from models import EveType


def memcache_type_key(typeId, options=None):
    if options is None:
        options = {}
    return "prices:%s:%s" % (options.get('solarsystem_id', '-1'), typeId)


def get_cached_values(eve_types, options=None):
    "Get Cached values given the eve_types"
    found = {}
    for eve_type in eve_types:
        key = memcache_type_key(eve_type.type_id, options=options)
        obj = cache.get(key)
        if obj:
            found[eve_type.type_id] = obj
    return found


def get_market_values(eve_types, options=None):
    """
        Takes list of typeIds. Returns dict of pricing details with typeId as
        the key. Calls out to the eve-central.

        Example Return Value:
        {
            21574:{
             'all': {
                'avg': 254.83,
                'min': 254.83,
                'max': 254.83,
                'price': 254.83
             },
             'buy': {
                'avg': 5434414.43,
                'min': 5434414.43,
                'max': 5434414.43,
                'price': 5434414.43
             },
             'sell': {
                'avg': 10552957.04,
                'min': 10552957.04,
                'max': 10552957.04,
                'price': 10552957.04
             }
        }
    """
    if len(eve_types) == 0:
        return {}

    if options is None:
        options = {}

    market_prices = {}
    solarsystem_id = options.get('solarsystem_id', -1)
    for types in [eve_types[i:i + 100] for i in range(0, len(eve_types), 100)]:
        query = []
        query += ['typeid=%s' % str(x.type_id) for x in types]
        all_price_metric = 'percentile'
        if solarsystem_id == '-1':
            buy_price_metric = 'percentile'
            sell_price_metric = 'percentile'
            # Forge (for jita): 10000002
            # Metropolis (for hek): 10000042
            # Heimatar (for rens): 10000030
            # Sinq Laison region (for dodixie): 10000032
            # Domain (for amarr): 10000043
            query += ['regionlimit=10000002', 'regionlimit=10000042',
                      'regionlimit=10000030', 'regionlimit=10000032',
                      'regionlimit=10000043']
        else:
            buy_price_metric = 'max'
            sell_price_metric = 'min'
            query += ['usesystem=%s' % solarsystem_id]
        query_str = '&'.join(query)
        url = "http://api.eve-central.com/api/marketstat?%s" % query_str
        try:
            request = urllib2.Request(url)
            request.add_header('User-Agent', app.config['USER_AGENT'])
            response = urllib2.build_opener().open(request).read()
            stats = ET.fromstring(response).findall("./marketstat/type")

            for marketstat in stats:
                k = int(marketstat.attrib.get('id'))
                v = {}
                for stat_type in ['sell', 'buy', 'all']:
                    props = {}
                    for stat in marketstat.find(stat_type):
                        props[stat.tag] = float(stat.text)
                    v[stat_type] = props
                v['all']['price'] = v['all'][all_price_metric]
                v['buy']['price'] = v['buy'][buy_price_metric]
                v['sell']['price'] = v['sell'][sell_price_metric]
                market_prices[k] = v

                # Cache for up to 10 hours
                cache.set(memcache_type_key(k, options=options),
                          v, timeout=10 * 60 * 60)
        except urllib2.HTTPError:
            pass
    return market_prices


def get_market_values_2(eve_types, options=None):
    """
        Takes list of typeIds. Returns dict of pricing details with typeId as
        the key. Calls out to the eve-marketdata.
        Example Return Value:
        {
            21574:{
             'all': {
                'avg': 254.83,
                'min': 254.83,
                'max': 254.83,
                'price': 254.83
             },
             'buy': {
                'avg': 5434414.43,
                'min': 5434414.43,
                'max': 5434414.43,
                'price': 5434414.43
             },
             'sell': {
                'avg': 10552957.04,
                'min': 10552957.04,
                'max': 10552957.04,
                'price': 10552957.04
             }
        }
    """
    if len(eve_types) == 0:
        return {}

    if options is None:
        options = {}

    market_prices = {}
    solarsystem_id = options.get('solarsystem_id', '-1')
    for types in [eve_types[i:i + 200] for i in range(0, len(eve_types), 200)]:
        typeIds_str = 'type_ids=%s' % ','.join(str(x.type_id) for x in types)
        query = ['typeid=%s' % typeIds_str]

        if solarsystem_id != '-1':
            query += ['usesystem=%s' % solarsystem_id]

            solarsystem_ids_str = ','.join(
                [str(options.get('solarsystem_id', 30000142))])
            query += ['solarsystem_ids=%s' % solarsystem_ids_str]
        query_str = '&'.join(query)

        url = "http://api.eve-marketdata.com/api/item_prices2.json?" \
            "char_name=magerawr&buysell=a&%s" % (query_str)
        try:
            request = urllib2.Request(url)
            request.add_header('User-Agent', app.config['USER_AGENT'])
            response = json.loads(urllib2.build_opener().open(request).read())

            for row in response['emd']['result']:
                row = row['row']
                k = int(row['typeID'])
                if k not in market_prices:
                    market_prices[k] = {}
                if row['buysell'] == 's':
                    price = float(row['price'])
                    market_prices[k]['sell'] = {
                        'avg': price,
                        'min': price,
                        'max': price,
                    }
                elif row['buysell'] == 'b':
                    price = float(row['price'])
                    market_prices[k]['buy'] = {
                        'avg': price,
                        'min': price,
                        'max': price,
                    }

            for typeId, prices in market_prices.iteritems():
                avg = (prices['sell']['avg'] + prices['buy']['avg']) / 2
                market_prices[typeId]['all'] = {
                    'avg': avg,
                    'min': avg,
                    'max': avg,
                    'price': avg,
                }
                market_prices[typeId]['buy']['price'] = \
                    market_prices[typeId]['buy']['max']
                market_prices[typeId]['sell']['price'] = \
                    market_prices[typeId]['sell']['min']

                # Cache for up to 10 hours
                cache.set(
                    memcache_type_key(typeId, options=options),
                    prices, timeout=10 * 60 * 60)
        except urllib2.HTTPError:
            pass
    return market_prices


def get_invalid_values(eve_types, options=None):
    invalid_items = {}
    for eve_type in eve_types:
        if eve_type.props.get('market') is False:
            zeroed_price = {'avg': 0, 'min': 0, 'max': 0, 'price': 0}
            price_info = {
                'buy': zeroed_price.copy(),
                'sell': zeroed_price.copy(),
                'all': zeroed_price.copy(),
            }
            invalid_items[eve_type.type_id] = price_info
    return invalid_items


def get_componentized_values(eve_types, options=None):
    componentized_items = {}
    for eve_type in eve_types:
        if 'components' in eve_type.props:
            component_types = [
                EveType(c['materialTypeID'], count=c['quantity'])
                for c in eve_type.props['components']]

            populate_market_values(
                component_types,
                methods=[
                    get_cached_values, get_market_values, get_market_values_2],
                options=options)
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
                            component.pricing_info[market_type][stat] * \
                            component.count
            componentized_items[eve_type.type_id] = complete_price_data
            # Cache for up to 10 hours
            cache.set(
                memcache_type_key(eve_type.type_id, options=options),
                complete_price_data,
                timeout=10 * 60 * 60)

    return componentized_items


def populate_market_values(eve_types, methods=None, options=None):
    unpopulated_types = list(eve_types)
    if methods is None:
        methods = [
            get_invalid_values, get_cached_values, get_componentized_values,
            get_market_values, get_market_values_2]
    for pricing_method in methods:
        if len(unpopulated_types) == 0:
            break
        # returns a dict with {type_id: pricing_info}
        prices = pricing_method(unpopulated_types, options=options)
        app.logger.debug(
            "Found %s/%s items using method: %s", len(prices),
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
