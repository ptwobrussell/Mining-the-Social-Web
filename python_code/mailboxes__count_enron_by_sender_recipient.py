# -*- coding: utf-8 -*-

import sys
import couchdb
from couchdb.design import ViewDefinition

server = couchdb.Server('http://localhost:5984')
db = server[sys.argv[1]]


def senderRecipientCountMapper(doc):
    if doc.get('From') and doc.get('To'):
        for recipient in doc['To']:
            yield ([doc['From'], recipient], 1)


def summingReducer(keys, values, rereduce):
    return sum(values)


view = ViewDefinition('index', 'doc_count_by_sender_recipient',
                      senderRecipientCountMapper, reduce_fun=summingReducer,
                      language='python')
view.sync(db)

# print out a nicely formatted table

print 'Sender'.ljust(40), 'Recipient'.ljust(40), 'Count'.rjust(5)
print '-' * 90
for row in db.view('index/doc_count_by_sender_recipient', group=True):
    print row.key[0].ljust(40), row.key[1].ljust(40), str(row.value).rjust(5)
