#!/usr/bin/env python
# This is a script intended to be ran only when there are updates to the item
# database. The results are dumped into a file as JSON to be read by the app.
#
# This script requires an installed (and updated) copy of Eve Online. This
# requires Reverence, a tool which looks at the game cache to get up-to-date
# data. URL: https://github.com/ntt/reverence/

import json
from reverence import blue, const


if __name__ == '__main__':

    COMP_TYPES = [const.groupSupercarrier,
                  const.groupCarrier,
                  const.groupTitan,
                  const.groupDreadnought,
                  const.groupCapitalIndustrialShip]
    EVEPATH = '/Applications/EVE Online.app/Contents/Resources/' \
              'EVE Online.app/Contents/Resources/transgaming/c_drive/' \
              'Program Files/CCP/EVE'
    # EVEPATH = "C:/EVE"

    eve = blue.EVE(EVEPATH)
    cfg = eve.getconfigmgr()

    all_types = []
    for invtype in cfg.invtypes:
        print("Populating info for: %s" % invtype.typeName.encode('utf-8'))

        hasMarket = invtype.marketGroupID is not None
        d = {
            'typeID': invtype.typeID,
            'groupID': invtype.groupID,
            'typeName': invtype.typeName,
            'volume': invtype.volume,
            'market': hasMarket,
        }

        # super carrier, carrier, titan, dread, rorq
        if all([invtype.groupID in COMP_TYPES,
                invtype.typeID in cfg.invtypematerials]):

            d['components'] = [{'typeID': typeID,
                                'materialTypeID': materialTypeID,
                                'quantity': qty}
                               for typeID, materialTypeID, qty
                               in cfg.invtypematerials[invtype.typeID]]

        all_types.append(d)

    with open('data/types.json', 'w') as f:
        f.write(json.dumps(all_types, indent=2))
