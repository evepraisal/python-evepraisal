#!/usr/bin/env python
# This is a script intended to be ran only when there are updates to the item
# database. The results are dumped into a file as JSON to be read by the app.
#
# Public mySQL access to this data can be found here:
# http://wiki.eve-id.net/CCP_Database_Dump_Resources

import json
import mysql.connector


if __name__ == '__main__':
    config = {
      'user': 'evedump',
      'password': 'evedump1234',
      'host': 'db.descention.net',
      'database': 'evedump',
      'raise_on_warnings': True,
    }

    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    query = ("SELECT typeID, groupID, typeName FROM invTypes;")
    cursor.execute(query)

    all_types = {}
    for (typeID, groupID, typeName) in cursor:
        all_types[typeName.strip().lower()] = {'typeID': typeID,
                                               'groupID': groupID,
                                               'typeName': typeName}

    with open('data/types.json', 'w') as f:
        f.write(json.dumps(all_types, indent=2))

    cnx.close()
