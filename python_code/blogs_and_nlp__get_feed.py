# -*- coding: utf-8 -*-

import sys
from datetime import datetime as dt
import json
import feedparser
from BeautifulSoup import BeautifulStoneSoup
from nltk import clean_html

FEED_URL = sys.argv[1]


def cleanHtml(html):
    return BeautifulStoneSoup(clean_html(html),
                              convertEntities=BeautifulStoneSoup.HTML_ENTITIES).decode()


fp = feedparser.parse(FEED_URL)

print "Fetched %s entries from '%s'" % (len(fp.entries[0].title), fp.feed.title)

blog_posts = []
for e in fp.entries:

    blog_posts.append({'title': e.title, 'content'
                      : cleanHtml(e.content[0].value), 'link': e.links[0].href})

out_file = '%s__%s' % (fp.feed.title, dt.utcnow())
f = open(out_file, 'w')
f.write(json.dumps(blog_posts))
f.close()

print 'Wrote output file to %s' % (out_file, )
