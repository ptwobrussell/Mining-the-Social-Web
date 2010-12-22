# -*- coding: utf-8 -*-

import sys
import httplib
from urllib import quote
import json

DB = sys.argv[1]
QUERY = sys.argv[2]

#  The body of a JavaScript-based design document we'll create

dd = \
    {'fulltext': {'by_subject': {'index': '''function(doc) { 
                            var ret=new Document(); 
                            ret.add(doc.Subject); 
                            return ret 
                        }'''},
     'by_content': {'index': '''function(doc) { 
                            var ret=new Document(); 
                            for (var i=0; i < doc.parts.length; i++) {
                                ret.add(doc.parts[i].content); 
                            }
                            return ret 
                        }'''}}}

#  Create a design document that'll be identified as "_design/lucene"
#  The equivalent of the following in a terminal:
#  $ curl -X PUT http://localhost:5984/DB/_design/lucene -d @dd.json

try:
    conn = httplib.HTTPConnection('localhost', 5984)
    conn.request('PUT', '/%s/_design/lucene' % (DB, ), json.dumps(dd))
    response = conn.getresponse()
finally:
    conn.close()

if response.status != 201:  #  Created
    print 'Unable to create design document: %s %s' % (response.status,
            response.reason)
    sys.exit()

#  Querying the design document is nearly the same as usual except that you reference
#  couchdb-lucene's _fti HTTP handler
#  $ curl http://localhost:5984/DB/_fti/_design/lucene/by_subject?q=QUERY

try:
    conn.request('GET', '/%s/_fti/_design/lucene/by_subject?q=%s' % (DB,
                 quote(QUERY)))
    response = conn.getresponse()
    if response.status == 200:
        response_body = json.loads(response.read())
        print json.dumps(response_body, indent=4)
    else:
        print 'An error occurred fetching the response: %s %s' \
            % (response.status, response.reason)
finally:
    conn.close()
