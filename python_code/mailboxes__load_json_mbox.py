# -*- coding: utf-8 -*-

import sys
import couchdb
try:
    import jsonlib2 as json
except ImportError:
    import json

server = couchdb.Server('http://localhost:5984')
jsonified_mbox = sys.argv[1]  # enron.mbox.json
DB = jsonified_mbox.split('.')[0]

db = server.create(DB)
docs = json.loads(open(jsonified_mbox).read())
db.update(docs, all_or_nothing=True)
