# -*- coding: utf-8 -*-

import sys
import couchdb
from couchdb.design import ViewDefinition

# Query out the documents at a given group level of interest

server = couchdb.Server('http://localhost:5984')
DB = sys.argv[1]
db = server[DB]
docs = db.view('index/doc_count_by_date_time', group_level=3)  # group by year, month, day

# Now, load the documents keyed by [year, month, day] into a new database

db_scratch = server.create(DB + '-num-per-day')
db_scratch.update(docs)


def transposeMapper(doc):
    yield (doc['value'], doc['key'])


view = ViewDefinition('index', 'num_per_day', transposeMapper, language='python')
view.sync(db_scratch)

print 'Date\t\tCount'
print '-' * 25
for row in db_scratch.view('index/num_per_day'):
    if row.key > 10:  # display stats where more than 10 messages were sent
        print '%s-%s-%s\t\t%s' % tuple(row.value + [row.key])
