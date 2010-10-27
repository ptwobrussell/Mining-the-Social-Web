# -*- coding: utf-8 -*-

import sys
from random import sample
import couchdb
from couchdb.design import ViewDefinition
import twitter
from twitter.oauth_dance import oauth_dance

server = couchdb.Server('http://localhost:5984')
DB = sys.argv[1]
db = server[DB]
SAMPLE_SIZE = 25
if len(sys.argv) > 2:
    SAMPLE_SIZE = int(sys.argv[2])

# Map entities in tweets to the docs that they appear in


def entityCountMapper(doc):
    if doc.get('id') and doc.get('text'):
        yield (doc['id'], doc['text'])


view = ViewDefinition('index', 'tweet_id', entityCountMapper, language='python')
view.sync(db)

# randomly select some tweets, but intentionally do not include direct replies

tweet_ids_text = sample([(int(kv['key']), kv['value']) for kv in
                        db.view('index/tweet_id') if kv['value'][0] != '@'],
                        SAMPLE_SIZE)

# now, determine how many of the tweets have been retweed ~200 times,
# which is the number of results returned via an initial API request...

# Go to http://twitter.com/apps/new to create an app and get these items

consumer_key = ''
consumer_secret = ''

# authenticate with the twitter api

(oauth_token, oauth_token_secret) = oauth_dance('MiningTheSocialWeb',
        consumer_key, consumer_secret)

t = twitter.Twitter(domain='api.twitter.com', api_version='1',
                    auth=twitter.oauth.OAuth(oauth_token, oauth_token_secret,
                    consumer_key, consumer_secret))

# protecting against Twitter API outages, etc. is omitted for clarity

stats = []
for (tweet_id, tweet_text) in tweet_ids_text:

    # could fetch multiple pages worth of results here via the "page" parameter

    response = t.statuses.__getattr__(str(tweet_id)).retweeted_by(count=200)  # twitter module "workaround"
    retweeted_by = []
    for r in response:
        retweeted_by.append(r['screen_name'])
    stats.append({
        'id': tweet_id,
        'tweet_text': tweet_text,
        'num_retweets': len(retweeted_by),
        'retweeted_by': retweeted_by,
        })

print 'Retweets'.ljust(10), 'Tweet Id'.ljust(10), 'Tweet'.ljust(150)
print '-' * 170
stats = sorted(stats, key=lambda x: x['num_retweets'])
for stat in stats:
    print str(len(stat['retweeted_by'])).ljust(10), str(stat['id']).ljust(10), \
        stat['tweet_text'].ljust(150)

num_retweeted = len([stat for stat in stats if stat['num_retweets'] > 0]) * 1.0
print 'Retweet/Tweet Ratio', num_retweeted / SAMPLE_SIZE
