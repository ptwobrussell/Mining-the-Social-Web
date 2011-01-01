# -*- coding: utf-8 -*-

import os
import sys
import buzz
from BeautifulSoup import BeautifulStoneSoup
from nltk import clean_html
import couchdb
import json

USER = sys.argv[1]

MAX_RESULTS = 100

# Helper function for removing html and converting escaped entities. 
# Returns UTF-8

def cleanHtml(html):
    return BeautifulStoneSoup(clean_html(html),
            convertEntities=BeautifulStoneSoup.HTML_ENTITIES).contents[0]


client = buzz.Client()
posts_data = client.posts(type_id='@public', 
                          user_id=USER, 
                          max_results=MAX_RESULTS).data

posts = []
for p in posts_data:

    # Fetching lots of comments for lots of posts could take a little 
    # bit of time. Thread pool code from mailboxes__CouchDBBulkReader.py could 
    # be adapted for use here.

    comments = [{'name': c.actor.name, 'content': cleanHtml(c.content)} for c in
                p.comments().data]
    link = p.uri
    post = {
        'title': cleanHtml(p.title),
        'content': cleanHtml(p.content),
        'comments': comments,
        'link': link,
        }
    posts.append(post)

# Store out to a local file as json data if you prefer

if not os.path.isdir('out'):
    os.mkdir('out')

filename = os.path.join('out', USER + '.buzz')
f = open(filename, 'w')
f.write(json.dumps(posts))
f.close()

print >> sys.stderr, "Data written to", f.name

# Or store it somewhere like CouchDB like so...

# server = couchdb.Server('http://localhost:5984')
# DB = 'buzz-' + USER
# db = server.create(DB)
# db.update(posts, all_or_nothing=True)
