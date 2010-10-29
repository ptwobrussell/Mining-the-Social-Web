# -*- coding: utf-8 -*-

import sys
import couchdb
from couchdb.design import ViewDefinition

server = couchdb.Server('http://localhost:5984')
db = server[sys.argv[1]]


def dateTimeCountMapper(doc):
    from dateutil.parser import parse
    from datetime import datetime as dt
    if doc.get('Date'):
        _date = list(dt.timetuple(parse(doc['Date']))[:-3])
        yield (_date, 1)


def summingReducer(keys, values, rereduce):
    return sum(values)


view = ViewDefinition('index', 'doc_count_by_date_time', dateTimeCountMapper,
                      reduce_fun=summingReducer, language='python')
view.sync(db)

# print out message counts by time slice

print 'Date\t\tCount'
print '-' * 25
# group by year, month, day
for row in db.view('index/doc_count_by_date_time', group_level=3):  
    print '%s\t\t%s' % (row.key, row.value)
