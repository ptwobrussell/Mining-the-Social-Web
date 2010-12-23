# -*- coding: utf-8 -*-

# XXX: This code is just cobbled together from other code lying around without much too much thought. 
# It could definititely be refactored for the better

# XXX: This code needs to be retested.

import os
import sys
import couchdb
import time
import redis
import twitter
import networkx as nx
import json
from twitter__login import login
from twitter__util import getRedisIdByScreenName
from twitter__util import makeTwitterRequest
from couchdb.design import ViewDefinition

DB = sys.argv[1]

try:
    server = couchdb.Server('http://localhost:5984')
    db = server[DB]
except couchdb.http.ResourceNotFound, e:
    print >> sys.stderr, """CouchDB database '%s' not found. 
Please check that the database exists and try again.""" % DB
    sys.exit(1)

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
            yield [um['screen_name'].lower(), None]

    # Emit the tweet author

    yield [doc['from_user'].lower(), None]


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

t = login()

r = redis.Redis()

count = 0
for screen_name in screen_names:

    ids = []
    cursor = -1
    while cursor != 0:
        try:
            response = makeTwitterRequest(t, 
                                          t.friends.ids, 
                                          screen_name=screen_name, 
                                          cursor=cursor)
            ids += response['ids']
            cursor = response['next_cursor']
            print >> sys.stderr, 'Fetched %i ids for %s' % (len(ids), screen_name)
        except twitter.api.TwitterHTTPError, e:
            if e.e.code == 404:
                print >> sys.stderr, "404 Error with screen_name '%s'. Continuing." % screen_name
                break

    # Store the ids into Redis

    [r.sadd(getRedisIdByScreenName(screen_name, 'friend_ids'), _id) for _id in
     ids]

    count += 1
    print >> sys.stderr, '\t\tFetched friends for %s / %s' % (count, len(screen_names))

print >> sys.stderr, 'Done fetching friend ids...'

####################################
# Resolve screen_names for user_ids
####################################

while len(screen_names) > 0:
    (screen_names_str, screen_names) = (','.join(screen_names[:100]),
                                        screen_names[100:])

    response = makeTwitterRequest(t,
                                  t.users.lookup,
                                  screen_name=screen_names_str)

    if type(response) is dict:  # Handle api quirk
        response = [response]
    r.mset(dict([(getRedisIdByScreenName(resp['screen_name'], 'info.json'),
           json.dumps(resp)) for resp in response]))

    #print len(response)

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
    print >> sys.stderr, 'Processing', screen_name

    try:
        friend_ids = list(r.smembers(getRedisIdByScreenName(screen_name,
                          'friend_ids')))
        print >> sys.stderr, "Adding edge: %s, %s" % (str(user_id), str(friend_id))
        [g.add_edge(user_id, friend_id) for friend_id in friend_ids if friend_id
         in ids_of_interest]
    except Exception, e:
        print >> sys.stderr, 'No friend information available. Skipping', screen_name

# store graph to disk by pickling it...

if not os.path.isdir('out'):
    os.mkdir('out')

filename = os.path.join('out', DB + '.gpickle')
nx.write_gpickle(g, filename)

print >> sys.stderr, 'Pickle file stored in: %s' % filename

# you can read it back out like this...
# g = nx.read_gpickle(os.path.join('out', DB + '.gpickle'))
