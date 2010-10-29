# -*- coding: utf-8 -*-

import sys
import httplib
from urllib import quote
import json
import couchdb
import twitter

DB = sys.argv[1]
USER = sys.argv[2]

# query by term

try:
    conn = httplib.HTTPConnection('localhost', 5984)
    conn.request('GET', '/%s/_fti/_design/lucene/by_text?q=%s' % (DB,
                 quote(USER)))
    response = conn.getresponse()
    if response.status == 200:
        response_body = json.loads(response.read())
    else:
        print 'An error occurred fetching the response: %s %s' \
            % (response.status, response.reason)
finally:
    conn.close()

doc_ids = [row['id'] for row in response_body['rows']]

# pull the tweets from CouchDB

server = couchdb.Server('http://localhost:5984')
db = server['tweets-user-timeline-timoreilly']
tweets = [db.get(doc_id) for doc_id in doc_ids]

# mine out the in_reply_to_status_id fields and fetch those tweets as a batch request

conversation = sorted([(tweet['_id'], int(tweet['in_reply_to_status_id']))
                      for tweet in tweets if tweet['in_reply_to_status_id']
                      is not None], key=lambda x: x[1])
min_conversation_id = min([int(i[1]) for i in conversation if i[1] is not None])
max_conversation_id = max([int(i[1]) for i in conversation if i[1] is not None])

# Pull tweets from other user using user timeline API to minimize API expenses...
# Note: robust error handling with the handleTwitterHTTPError function omitted for brevity

# Go to http://twitter.com/apps/new to create an app and get these items

consumer_key = ''
consumer_secret = ''

# authenticate with the twitter api

(oauth_token, oauth_token_secret) = oauth_dance('MiningTheSocialWeb',
        consumer_key, consumer_secret)

t = twitter.Twitter(domain='api.twitter.com', api_version='1',
                    auth=twitter.oauth.OAuth(oauth_token, oauth_token_secret,
                    consumer_key, consumer_secret))

reply_tweets = []
for page in range(1, 4):
    reply_tweets.extend(t.statuses.user_timeline(
        count=200,
        since_id=min_conversation_id,
        max_id=max_conversation_id,
        skip_users='true',
        id=USER,
        page=page,
        ))

for (doc_id, in_reply_to_id) in conversation:
    try:
        print [rt for rt in reply_tweets if rt['id'] == in_reply_to_id][0]['text']
    except:
        print '<<%s>>' % (in_reply_to_id, )
    print db.get(doc_id)['text']
    print
