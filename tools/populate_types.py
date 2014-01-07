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

    COMP_TYPES = [659, 547, 30, 485, 883]
    EVEPATH = '/Applications/EVE Online.app/Contents/Resources/' \
              'EVE Online.app/Contents/Resources/transgaming/c_drive/' \
              'Program Files/CCP/EVE'
    # EVEPATH = "C:/EVE"

    eve = blue.EVE(EVEPATH)
    cfg = eve.getconfigmgr()

    all_types = []
    for (typeID, groupID, typeName, marketGroupID, volume) in \
            cfg.invtypes.Select(
                'typeID', 'groupID', 'typeName', 'marketGroupID', 'volume'):
        print("Populating info for: %s" % typeName.encode('utf-8'))

        hasMarket = marketGroupID is not None
        d = {
            'typeID': typeID,
            'groupID': groupID,
            'typeName': typeName,
            'volume': volume,
            'market': hasMarket,
        }

        # super carrier, carrier, titan, dread, rorq
        if groupID in COMP_TYPES and typeID in cfg.invtypematerials:
            components = []
            for typeID, materialTypeID, qty in cfg.invtypematerials[typeID]:
                components.append({
                    'typeID': typeID,
                    'materialTypeID': materialTypeID,
                    'quantity': qty,
                })

            d['components'] = components
        name_lower = typeName.lower()
        all_types.append(d)

    with open('data/types.json', 'w') as f:
        f.write(json.dumps(all_types, indent=2))
