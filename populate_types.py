#!/usr/bin/env python
import json
import mysql.connector

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
