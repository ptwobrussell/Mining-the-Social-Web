# -*- coding: utf-8 -*-

# XXX: This code needs to be retested. It was spliced together from multiple scripts previously
# XXX: This code is just cobbled together from other code lying around without much thought. It could
#     definititely be refactored for the better

import sys
import couchdb
from couchdb.design import ViewDefinition
import time
import twitter
from twitter.oauth_dance import oauth_dance
import redis
import networkx as nx
import json

DB = sys.argv[1]
db = couchdb.Server('http://localhost:5984')[DB]

#########################################################
# Compute the set of user mentions and tweet authors
#########################################################


def uniqueMentionsAndAuthorsMapper(doc):
    if not doc.get('entities'):
        import twitter_text
        extractor = twitter_text.Extractor(doc['text'])
        doc['entities'] = {'user_mentions': [um for um in
                           extractor.extract_mentioned_screen_names_with_indices()]}

    # Emit the @mentions

    if doc['entities'].get('user_mentions'):
        for um in doc['entities']['user_mentions']:
            yield [um['screen_name'], None]

    # Emit the tweet author

    yield [doc['from_user'], None]


def nullReducer(keys, values, rereduce):
    return None


view = ViewDefinition('index', 'unique_mentions_and_authors',
                      uniqueMentionsAndAuthorsMapper, reduce_fun=nullReducer,
                      language='python')
view.sync(db)

screen_names = [row['key'] for row in db.view('index/unique_mentions_and_authors'
                , group=True)]

#############################################
# Harvest the friends for each screen_name
# Can't take a shortcut and resolve using from_user_id in
# the search results.
# See http://code.google.com/p/twitter-api/issues/detail?id=214
#############################################

# Go to http://twitter.com/apps/new to create an app and get these items

consumer_key = ''
consumer_secret = ''

friends_limit = 10000

(oauth_token, oauth_token_secret) = oauth_dance('MiningTheSocialWeb',
        consumer_key, consumer_secret)

t = twitter.Twitter(domain='api.twitter.com', api_version='1',
                    auth=twitter.oauth.OAuth(oauth_token, oauth_token_secret,
                    consumer_key, consumer_secret))


def handleTwitterHTTPError(e, wait_period=2):
    if wait_period > 3600:  # 1 hour
        print 'Too many retries. Quitting.'
        raise e

    if e.e.code == 401:
        print 'Encountered 401 Error (Not Authorized)'
        print 'User %s is protecting their tweets. Skipping...' % (screen_name, )
        return None
    elif e.e.code in (502, 503):
        print 'Encountered %i Error. Will retry in %i seconds' % (e.e.code,
                wait_period)
        time.sleep(wait_period)
        wait_period *= 1.5
        return wait_period
    elif t.account.rate_limit_status()['remaining_hits'] == 0:
        status = t.account.rate_limit_status()
        now = time.time()  # UTC
        when_rate_limit_resets = status['reset_time_in_seconds']  # UTC
        sleep_time = when_rate_limit_resets - now
        print 'Rate limit reached: sleeping for %i secs' % (sleep_time, )
        time.sleep(sleep_time)
        return 2
    else:
        print 'Encountered unhandled error (%i). Trying again in %s secs' \
            % (e.e.code, wait_period)
        time.sleep(wait_period)
        wait_period *= 1.5
        return wait_period


def getRedisIdByScreenName(screen_name, key_name):
    return 'screen_name$' + screen_name + '$' + key_name


r = redis.Redis()

count = 0
for screen_name in screen_names:

    ids = []
    wait_period = 2  # secs
    cursor = -1

    while cursor != 0:
        if wait_period > 3600:  # 1 hour
            print 'Too many retries. Quitting'
            exit()

        while True:
            try:
                response = t.friends.ids(screen_name=screen_name, cursor=cursor)
                ids += response['ids']
                wait_period = 2
            except twitter.api.TwitterHTTPError, e:
                wait_period = handleTwitterHTTPError(e, wait_period)
                if wait_period is None:
                    break

        cursor = response['next_cursor']
        print 'Fetched %i ids for %s' % (len(ids), screen_name)
        if len(ids) >= friends_limit:
            break

    # Store the ids into Redis

    [r.sadd(getRedisIdByScreenName(screen_name, 'friend_ids'), _id) for _id in
     ids]

    count += 1
    print '\t\tFetched friends for %s / %s' % (count, len(screen_names))

print 'Done fetching friend ids...'

####################################
# Resolve screen_names for user_ids
####################################

while len(screen_names) > 0:
    (screen_names_str, screen_names) = (','.join(screen_names[:100]),
                                        screen_names[100:])

    wait_period = 2
    while True:
        try:
            response = t.users.lookup(screen_name=screen_names_str)

            wait_period = 2
            break
        except twitter.api.TwitterHTTPError, e:
            wait_period = handleTwitterHTTPError(e, wait_period)
            if wait_period is None:
                break

    if type(response) is dict:  # Handle api quirk
        response = [response]
    r.mset(dict([(getRedisIdByScreenName(resp['screen_name'], 'info.json'),
           json.dumps(resp)) for resp in response]))

    print len(response)

###################################################
# Finally, build out a graph of friend_ids
###################################################

screen_names_to_user_ids = []
for sn in screen_names:
    data = r.get(getRedisIdByScreenName(sn, 'info.json'))
    if not data:
        continue
    json_data = json.loads(data)
    screen_names_to_user_ids.append((sn, json_data['id']))

g = nx.Graph()
ids_of_interest = [str(user_id) for (screen_name, user_id) in
                   screen_names_to_user_ids]
for (screen_name, user_id) in screen_names_to_user_ids:
    print 'Processing', screen_name

    try:
        friend_ids = list(r.smembers(getRedisIdByScreenName(screen_name,
                          'friend_ids')))
        [g.add_edge(user_id, friend_id) for friend_id in friend_ids if friend_id
         in ids_of_interest]
    except Exception, e:
        print 'No friend information available. Skipping', screen_name

# store graph to disk by pickling it...

nx.write_gpickle(g, DB + '.gpickle')

# you can read it back out like this...
# g = nx.read_gpickle(DB + '.gpickle')
