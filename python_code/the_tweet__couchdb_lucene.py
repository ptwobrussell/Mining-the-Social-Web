# -*- coding: utf-8 -*-

import sys
import httplib
from urllib import quote
import json
import couchdb

DB = sys.argv[1]
QUERY = sys.argv[2]

#  The body of a JavaScript-based design document we'll create

dd = \
    {'fulltext': {'by_text': {'index': '''function(doc) { 
                            var ret=new Document(); 
                            ret.add(doc.text); 
                            return ret 
                        }'''}}}

try:
    server = couchdb.Server('http://localhost:5984')
    db = server[DB]
except couchdb.http.ResourceNotFound, e:
    print """CouchDB database '%s' not found. 
Please check that the database exists and try again.""" % DB
    sys.exit(1)

try:
    conn = httplib.HTTPConnection('localhost', 5984)
    conn.request('GET', '/%s/_design/lucene' % (DB, ))
    response = conn.getresponse()
finally:
    conn.close()

#  If the design document did not exist create one that'll be
#  identified as "_design/lucene". The equivalent of the following 
#  in a terminal:
#  $ curl -X PUT http://localhost:5984/DB/_design/lucene -d @dd.json
if response.status == 404:
    try:
        conn = httplib.HTTPConnection('localhost', 5984)
        conn.request('PUT', '/%s/_design/lucene' % (DB, ), json.dumps(dd))
        response = conn.getresponse()
    
        if response.status != 201:
            print 'Unable to create design document: %s %s' % (response.status,
                   response.reason)
            sys.exit(1)
    finally:
        conn.close()

#  Querying the design document is nearly the same as usual except that you reference
#  couchdb-lucene's _fti HTTP handler
#  $ curl http://localhost:5984/DB/_fti/_design/lucene/by_subject?q=QUERY

try:
    conn.request('GET', '/%s/_fti/_design/lucene/by_text?q=%s' % (DB,
                 quote(QUERY)))
    response = conn.getresponse()
    if response.status == 200:
        response_body = json.loads(response.read())
    else:
        print 'An error occurred fetching the response: %s %s' \
            % (response.status, response.reason)
        print 'Make sure your couchdb-lucene server is running.'
        sys.exit(1)
finally:
    conn.close()

doc_ids = [row['id'] for row in response_body['rows']]

# pull the tweets from CouchDB and extract the text for display

tweets = [db.get(doc_id)['text'] for doc_id in doc_ids]
for tweet in tweets:
    print tweet
    print
