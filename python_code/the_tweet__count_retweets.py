# -*- coding: utf-8 -*-

import sys
import couchdb
from couchdb.design import ViewDefinition

server = couchdb.Server('http://localhost:5984')
DB = sys.argv[1]
db = server[DB]

if len(sys.argv) > 2 and sys.argv[2].isdigit():
    FREQ_THRESHOLD = int(sys.argv[2])
else:
    FREQ_THRESHOLD = 3

# Map entities in tweets to the docs that they appear in


def entityCountMapper(doc):
    if doc.get('text'):
        import re
        m = re.search(r"(RT|via)((?:\b\W*@\w+)+)", doc['text'])
        if m:
            entities = m.groups()[1].split()
            for entity in entities:
                yield (entity, [doc['_id'], doc['id']])
        else:
            yield ('@', [doc['_id'], doc['id']])


def summingReducer(keys, values, rereduce):
    if rereduce:
        return sum(values)
    else:
        return len(values)


view = ViewDefinition('index', 'retweet_entity_count_by_doc', entityCountMapper,
                      reduce_fun=summingReducer, language='python')
view.sync(db)

# Print out a nicely formatted table. Sorting by value in the client is cheap and easy
# if you're dealing with hundreds or low thousands of tweets

entities_freqs = sorted([(row.key, row.value) for row in
                        db.view('index/retweet_entity_count_by_doc',
                        group=True)], key=lambda x: x[1])

print 'Entity'.ljust(100), 'Count'.rjust(5)
print '-' * 110
for (entity, freq) in entities_freqs:
    if freq > FREQ_THRESHOLD and entity != '@':
        print entity.ljust(100), str(freq).rjust(5)
