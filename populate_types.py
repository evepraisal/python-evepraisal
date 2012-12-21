#!/usr/bin/env python
# This is a script intended to be ran only when there are updates to the item
# database. The results are dumped into a file as JSON to be read by the app.
#
# This script requires an installed (and updated) copy of Eve Online. This
# requires Reverence, a tool which looks at the game cache to get up-to-date
# data. URL: https://github.com/ntt/reverence/

import json
from reverence import blue


if __name__ == '__main__':

    EVEPATH = '/Applications/EVE Online.app/Contents/Resources/EVE Online.app/Contents/Resources/transgaming/c_drive/Program Files/CCP/EVE'
    # EVEPATH = "C:/EVE"

    eve = blue.EVE(EVEPATH)
    cfg = eve.getconfigmgr()
    all_types = {}

    # public_market_groups = []
    # for groupID, published in cfg.invgroups.Select('groupID', 'published'):
    #     if published:
    #         public_market_groups.append(groupID)

    # Groups that don't appear in the market
    nonMarketGroups = [314]

    for (typeID, groupID, typeName, marketGroupID, volume) in cfg.invtypes.Select('typeID',
                                                    'groupID', 'typeName', 'marketGroupID', 'volume'):
        # if groupID in public_market_groups:
        hasMarket = marketGroupID is not None
        all_types[typeName.strip().lower()] = {'typeID': typeID,
                                               'groupID': groupID,
                                               'typeName': typeName,
                                               'volume': volume,
                                               'market': hasMarket,
                                               }
    with open('data/types.json', 'w') as f:
        f.write(json.dumps(all_types, indent=2))
