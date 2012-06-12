# -*- coding: utf-8 -*-

import sys
import os
import pymongo
from pymongo import Connection

try:
    import jsonlib2 as json
except ImportError:
    import json

JSON_MBOX = sys.argv[1]  # i.e. enron.mbox.json
DB_NAME = os.path.basename(JSON_MBOX).split('.')[0]

connection = Connection('localhost', 27017)
db = connection[DB_NAME]

docs = json.loads(open(JSON_MBOX).read())

collection = db['messages']
for doc in docs:
    print str(doc)
	collection.insert(doc)