# -*- coding: utf-8 -*-

import sys
import couchdb
from couchdb.design import ViewDefinition
try:
    import jsonlib2 as json
except ImportError:
    import json

server = couchdb.Server('http://localhost:5984')
db = server[sys.argv[1]]


def dateTimeToDocMapper(doc):

    # Note that you need to include imports used by your mapper inside the function definition

    from dateutil.parser import parse
    from datetime import datetime as dt
    if doc.get('Date'):
        _date = list(dt.timetuple(parse(doc['Date']))[:-3])  # [year, month, day, hour, min, sec]
        yield (_date, doc)


view = ViewDefinition('index', 'by_date_time', dateTimeToDocMapper,
                      language='python')
view.sync(db)

# slice over items sorted by date

(start, end) = ([2001, 5, 28], [2001, 7, 4])
print 'Documents dated from %s-%s-%s to %s-%s-%s' % tuple(start + end)
docs = []
for row in db.view('index/by_date_time', startkey=start, endkey=end):
    docs.append(db.get(row.id))
print json.dumps(docs, indent=4)
