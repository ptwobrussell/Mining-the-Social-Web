# -*- coding: utf-8 -*-

import sys
import buzz  # XXX: Add to your PYTHONPATH since easy_install is not available
from BeautifulSoup import BeautifulStoneSoup
from nltk import clean_html
import couchdb
import json

USER = sys.argv[1]

# Helper function for removing html and converting escaped entities. Returns UTF-8


def cleanHtml(html):
    return BeautifulStoneSoup(clean_html(html),
                              convertEntities=BeautifulStoneSoup.HTML_ENTITIES).decode()


client = buzz.Client()
posts_data = client.posts(type_id='@public', user_id=USER, max_results=100).data

posts = []
for p in posts_data:

    # Fetching lots of comments for lots of posts could take a little bit of time. 
    # Thread pool code from XXX could be adapted for use here.

    comments = [{'name': c.actor.name, 'content': cleanHtml(c.content)} for c in
                p.comments().data]
    link = p.link['href']
    post = {
        'title': cleanHtml(p.title),
        'content': cleanHtml(p.content),
        'comments': comments,
        'link': link,
        }
    posts.append(post)

# Store out to a local file as json data if you prefer

f = open(USER + '.buzz', 'w')
f.write(json.dumps(posts))
f.close()

# Or store in CouchDB...

server = couchdb.Server('http://localhost:5984')
DB = 'buzz-' + USER
db = server.create(DB)
db.update(posts, all_or_nothing=True)
