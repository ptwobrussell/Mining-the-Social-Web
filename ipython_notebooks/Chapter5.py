# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <markdowncell>

# #Mining the Social Web, 1st Edition - The Tweet, The Whole Tweet, and Nothing But the Tweet (Chapter 5)
# 
# If you only have 10 seconds...
# 
# Twitter's new API will prevent you from running much of the code from _Mining the Social Web_, and this IPython Notebook shows you how to roll with the changes and adapt as painlessly as possible until an updated printing is available. In particular, it shows you how to authenticate before executing any API requests illustrated in this chapter and how to use the new search API amongst other things. It is highly recommended that you read the IPython Notebook file for Chapter 1 before attempting the examples in this chapter if you haven't already. One of the examples also presumes that you've run an example from Chapter 4 and stored some data in Redis that is recycled into this chapter.
# 
# If you have a couple of minutes...
# 
# Twitter is officially retiring v1.0 of their API as of March 2013 with v1.1 of the API being the new status quo. There are a few fundamental differences that social web miners that should consider (see Twitter's blog at https://dev.twitter.com/blog/changes-coming-to-twitter-api and https://dev.twitter.com/docs/api/1.1/overview) with the two changes that are most likely to affect an existing workflow being that authentication is now mandatory for *all* requests, rate-limiting being on a per resource basis (as opposed to an overall rate limit based on a fixed number of requests per unit time), various platform objects changing (for the better), and search semantics changing to a "pageless" approach. All in all, the v1.1 API looks much cleaner and more consistent, and it should be a good thing longer-term although it may cause interim pains for folks migrating to it.
# 
# The latest printing of Mining the Social Web (2012-02-22, Third release) reflects v1.0 of the API, and this document is intended to provide readers with updated examples from Chapter 5 of the book until a new printing provides updates.
# 
# Unlike the IPython Notebook for Chapter 1, there is no filler in this notebook at this time. See the Chapter 1 notebook for a good introduction to using the Twitter API and all that it entails.
# 
# As a reader of my book, I want you to know that I'm committed to helping you in any way that I can, so please reach out on Facebook at https://www.facebook.com/MiningTheSocialWeb or on Twitter at http://twitter.com/SocialWebMining if you have any questions or concerns in the meanwhile. I'd also love your feedback on whether or not you think that IPython Notebook is a good tool for tinkering with the source code for the book, because I'm strongly considering it as a supplement for each chapter.
# 
# Regards - Matthew A. Russell
# 
# 
# ## A Brief Technical Preamble
# 
# * You will need to set your PYTHONPATH environment variable to point to the 'python_code' folder for the GitHub source code when launching this notebook or some of the examples won't work, because they import utility code that's located there
# 
# * Note that this notebook doesn't repeatedly redefine a connection to the Twitter API. It creates a connection one time and resuses it throughout the remainder of the examples in the notebook
# 
# * Arguments that are typically passed in through the command line are hardcoded in the examples for convenience. CLI arguments are typically in ALL_CAPS, so they're easy to spot and change as needed
# 
# * For simplicity, examples that harvest data are limited to small numbers so that it's easier to use experiment with this notebook (given that @timoreilly, the principal subject of the examples, has vast numbers of followers)
# 
# * The parenthetical file names at the end of the captions for the examples correspond to files in the 'python_code' folder of the GitHub repository
# 
# * Just like you'd learn from reading the book, you'll need to have a CouchDB server running because several of the examples in this chapter store and fetch data from it
# 
# * The package twitter_text that is illustrated in some examples for extracting "tweet entities" is no longer necessary because the v1.1 API provides tweet entities, but the code still reflects it for compatibility with the current discussion in the book

# <markdowncell>

# Example 5-2. Extracting tweet entities with a little help from the twitter_text package (the_tweet__extract_tweet_entities.py)

# <codecell>

#################################################################################
# NOTE: The opt-in "include_entities" flag can be passed in as a keyword 
# argument to to t.statuses.show to have Twitter's API extract the entities 
# instead of using the getEntities function as described in this example like so:
#
# tweet = t.statuses.show(id=TWEET_ID, include_entities=1)
# 
# This is a case-in-point of Twitter's API constantly evolving to make the lives
# of developers easier. Their API slowly evolved quite a bit over the course of
# 2010 as Mining the Social Web was being written, and will no doubt continue
# to evolve and obsolete additional examples. Still, however, not all Twitter 
# APIs provide an opt-in parameter for extracting tweet entities (as of early
# January 2010 anyway), and it is likely the case that you'll need to perform 
# this work manually for histroical or archived data that was collected prior 
# to mid- to late-2010 unless 3rd party data providers perform the work for you.
#################################################################################

import sys
import json
import twitter_text # easy_install twitter-text-py
import twitter
from twitter__login import login

# Get a tweet id by clicking on status "Details" right off of twitter.com. 
# For example, http://twitter.com/#!/timoreilly/status/17386521699024896

TWEET_ID = '17386521699024896' # XXX: IPython Notebook cannot prompt for input

def getEntities(tweet):

    # Now extract various entities from it and build up a familiar structure

    extractor = twitter_text.Extractor(tweet['text'])

    # Note that the production Twitter API contains a few additional fields in
    # the entities hash that would require additional API calls to resolve

    entities = {}
    entities['user_mentions'] = []
    for um in extractor.extract_mentioned_screen_names_with_indices():
        entities['user_mentions'].append(um)

    entities['hashtags'] = []
    for ht in extractor.extract_hashtags_with_indices():

        # massage field name to match production twitter api

        ht['text'] = ht['hashtag']
        del ht['hashtag']
        entities['hashtags'].append(ht)

    entities['urls'] = []
    for url in extractor.extract_urls_with_indices():
        entities['urls'].append(url)

    return entities


# Fetch a tweet using an API method of your choice and mixin the entities

t = twitter.Twitter(domain='api.twitter.com', api_version='1.1')

tweet = t.statuses.show(id=TWEET_ID)

tweet['entities'] = getEntities(tweet)

print json.dumps(tweet, indent=4)

# <markdowncell>

# Example 5-3. Harvesting tweets from a user or public timeline (the_tweet__harvest_timeline.py)

# <codecell>

import sys
import time
import twitter
import couchdb
from couchdb.design import ViewDefinition
from twitter__login import login
from twitter__util import makeTwitterRequest
from twitter__util import getNextQueryMaxIdParam


TIMELINE_NAME = 'user' # XXX: IPython Notebook cannot prompt for input
MAX_PAGES = 2 # XXX: IPython Notebook cannot prompt for input
USER = 'timoreilly' # XXX: IPython Notebook cannot prompt for input

KW = {  # For the Twitter API call
    'count': 200,
    'trim_user': 'true',
    'include_rts' : 'true',
    'since_id' : 1,
    }

if TIMELINE_NAME == 'user':
    USER = sys.argv[3]
    KW['screen_name'] = USER
if TIMELINE_NAME == 'home' and MAX_PAGES > 4:
    MAX_PAGES = 4
if TIMELINE_NAME == 'user' and MAX_PAGES > 16:
    MAX_PAGES = 16

t = login()

# Establish a connection to a CouchDB database
server = couchdb.Server('http://localhost:5984')
DB = 'tweets-%s-timeline' % (TIMELINE_NAME, )

if USER:
    DB = '%s-%s' % (DB, USER)

try:
    db = server.create(DB)
except couchdb.http.PreconditionFailed, e:

    # Already exists, so append to it, keeping in mind that duplicates could occur

    db = server[DB]

    # Try to avoid appending duplicate data into the system by only retrieving tweets 
    # newer than the ones already in the system. A trivial mapper/reducer combination 
    # allows us to pull out the max tweet id which guards against duplicates for the 
    # home and user timelines. This is best practice for the Twitter v1.1 API
    # See https://dev.twitter.com/docs/working-with-timelines


    def idMapper(doc):
        yield (None, doc['id'])


    def maxFindingReducer(keys, values, rereduce):
        return max(values)


    view = ViewDefinition('index', 'max_tweet_id', idMapper, maxFindingReducer,
                          language='python')
    view.sync(db)

    KW['since_id'] = int([_id for _id in db.view('index/max_tweet_id')][0].value)

api_call = getattr(t.statuses, TIMELINE_NAME + '_timeline')
tweets = makeTwitterRequest(api_call, **KW)
db.update(tweets, all_or_nothing=True)
print 'Fetched %i tweets' % len(tweets)

page_num = 1
while page_num < MAX_PAGES and len(tweets) > 0:

    # Necessary for traversing the timeline in Twitter's v1.1 API.
    # See https://dev.twitter.com/docs/working-with-timelines
    KW['max_id'] = getNextQueryMaxIdParam(tweets)

    api_call = getattr(t.statuses, TIMELINE_NAME + '_timeline')
    tweets = makeTwitterRequest(api_call, **KW)
    db.update(tweets, all_or_nothing=True)
    print 'Fetched %i tweets' % len(tweets)
    page_num += 1

# <markdowncell>

# Example 5-4. Extracting entities from tweets and performing simple frequency analysis (the_tweet__count_entities_in_tweets.py)

# <codecell>

# Note: The Twitter v1.1 API includes tweet entities by default, so the use of the
# twitter_text package for parsing out tweet entities in this chapter is no longer
# relevant, but included for continuity with the text of the book.

import sys
import couchdb
from couchdb.design import ViewDefinition
from prettytable import PrettyTable

DB = 'tweets-user-timeline-timoreilly' # XXX: IPython Notebook cannot prompt for input

server = couchdb.Server('http://localhost:5984')
db = server[DB]

FREQ_THRESHOLD = 3 # XXX: IPython Notebook cannot prompt for input


# Map entities in tweets to the docs that they appear in

def entityCountMapper(doc):
    if not doc.get('entities'):
        import twitter_text

        def getEntities(tweet):

            # Now extract various entities from it and build up a familiar structure

            extractor = twitter_text.Extractor(tweet['text'])

            # Note that the production Twitter API contains a few additional fields in
            # the entities hash that would require additional API calls to resolve

            entities = {}
            entities['user_mentions'] = []
            for um in extractor.extract_mentioned_screen_names_with_indices():
                entities['user_mentions'].append(um)

            entities['hashtags'] = []
            for ht in extractor.extract_hashtags_with_indices():

                # Massage field name to match production twitter api

                ht['text'] = ht['hashtag']
                del ht['hashtag']
                entities['hashtags'].append(ht)

            entities['urls'] = []
            for url in extractor.extract_urls_with_indices():
                entities['urls'].append(url)

            return entities

        doc['entities'] = getEntities(doc)

    if doc['entities'].get('user_mentions'):
        for user_mention in doc['entities']['user_mentions']:
            yield ('@' + user_mention['screen_name'].lower(), [doc['_id'], doc['id']])
    if doc['entities'].get('hashtags'):
        for hashtag in doc['entities']['hashtags']:
            yield ('#' + hashtag['text'], [doc['_id'], doc['id']])
    if doc['entities'].get('urls'):
        for url in doc['entities']['urls']:
            yield (url['url'], [doc['_id'], doc['id']])


def summingReducer(keys, values, rereduce):
    if rereduce:
        return sum(values)
    else:
        return len(values)


view = ViewDefinition('index', 'entity_count_by_doc', entityCountMapper,
                      reduce_fun=summingReducer, language='python')
view.sync(db)

# Print out a nicely formatted table. Sorting by value in the client is cheap and easy
# if you're dealing with hundreds or low thousands of tweets

entities_freqs = sorted([(row.key, row.value) for row in
                        db.view('index/entity_count_by_doc', group=True)],
                        key=lambda x: x[1], reverse=True)

field_names = ['Entity', 'Count']
pt = PrettyTable(field_names=field_names)
pt.align = 'l'

for (entity, freq) in entities_freqs:
    if freq > FREQ_THRESHOLD:
        pt.add_row([entity, freq])

print pt

# <markdowncell>

# Example 5-5. Finding @mention tweet entities that are also friends (the_tweet__how_many_user_entities_are_friends.py)

# <codecell>

import json
import redis
import couchdb
import sys
from twitter__util import getRedisIdByScreenName
from twitter__util import getRedisIdByUserId

SCREEN_NAME = 'timoreilly' # XXX: IPython Notebook cannot prompt for input
THRESHOLD = 15 # XXX: IPython Notebook cannot prompt for input

# Connect using default settings for localhost

r = redis.Redis()

# Compute screen_names for friends

friend_ids = r.smembers(getRedisIdByScreenName(SCREEN_NAME, 'friend_ids'))
friend_screen_names = []
for friend_id in friend_ids:
    try:
        friend_screen_names.append(json.loads(r.get(getRedisIdByUserId(friend_id,
                                   'info.json')))['screen_name'].lower())
    except TypeError, e:
        continue  # not locally available in Redis - look it up or skip it

# Pull the  list of (entity, frequency) tuples from CouchDB

server = couchdb.Server('http://localhost:5984')
db = server['tweets-user-timeline-' + SCREEN_NAME]

entities_freqs = sorted([(row.key, row.value) for row in
                        db.view('index/entity_count_by_doc', group=True)],
                        key=lambda x: x[1])

# Keep only user entities with insufficient frequencies

user_entities = [(ef[0])[1:] for ef in entities_freqs if ef[0][0] == '@'
                 and ef[1] >= THRESHOLD]

# Do a set comparison

entities_who_are_friends = \
    set(user_entities).intersection(set(friend_screen_names))

entities_who_are_not_friends = \
    set(user_entities).difference(entities_who_are_friends)

print 'Number of user entities in tweets: %s' % (len(user_entities), )
print 'Number of user entities in tweets who are friends: %s' \
    % (len(entities_who_are_friends), )
for e in entities_who_are_friends:
    print '\t' + e
print 'Number of user entities in tweets who are not friends: %s' \
    % (len(entities_who_are_not_friends), )
for e in entities_who_are_not_friends:
    print '\t' + e

# <markdowncell>

# Example 5-7. Using couchdb-lucene to query tweet data (the_tweet__couchdb_lucene.py)

# <codecell>

import sys
import httplib
from urllib import quote
import json
import couchdb

DB = 'tweets-user-timeline-timoreilly' # XXX: IPython Notebook cannot prompt for input
QUERY = 'data' # XXX: IPython Notebook cannot prompt for input

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

# <markdowncell>

# Example 5-9. Reconstructing tweet discussion threads (the_tweet__reassemble_discussion_thread.py)

# <codecell>

import sys
import httplib
from urllib import quote
import json
import couchdb
from twitter__login import login
from twitter__util import makeTwitterRequest

DB = 'tweets-user-timeline-timoreilly' # XXX: IPython Notebook cannot prompt for input
USER = 'n2vip' # XXX: IPython Notebook cannot prompt for input

try:
    server = couchdb.Server('http://localhost:5984')
    db = server[DB]
except couchdb.http.ResourceNotFound, e:
    print >> sys.stderr, """CouchDB database '%s' not found. 
Please check that the database exists and try again.""" % DB
    sys.exit(1)

# query by term

try:
    conn = httplib.HTTPConnection('localhost', 5984)
    conn.request('GET', '/%s/_fti/_design/lucene/by_text?q=%s' % (DB,
                 quote(USER)))
    response = conn.getresponse()
    if response.status == 200:
        response_body = json.loads(response.read())
    else:
        print >> sys.stderr, 'An error occurred fetching the response: %s %s' \
            % (response.status, response.reason)
        sys.exit(1)
finally:
    conn.close()

doc_ids = [row['id'] for row in response_body['rows']]

# pull the tweets from CouchDB

tweets = [db.get(doc_id) for doc_id in doc_ids]

# mine out the in_reply_to_status_id_str fields and fetch those tweets as a batch request

conversation = sorted([(tweet['_id'], int(tweet['in_reply_to_status_id_str']))
                      for tweet in tweets if tweet['in_reply_to_status_id_str']
                      is not None], key=lambda x: x[1])
min_conversation_id = min([int(i[1]) for i in conversation if i[1] is not None])
max_conversation_id = max([int(i[1]) for i in conversation if i[1] is not None])

# Pull tweets from other user using user timeline API to minimize API expenses...

t = login()

reply_tweets = []
results = []
page = 1
while True:
    results = makeTwitterRequest(t.statuses.user_timeline,
        count=200,
        # Per <http://dev.twitter.com/doc/get/statuses/user_timeline>, some
        # caveats apply with the oldest id you can fetch using "since_id"
        since_id=min_conversation_id,
        max_id=max_conversation_id,
        skip_users='true',
        screen_name=USER,
        page=page)
    reply_tweets += results
    page += 1
    if len(results) == 0: 
        break

# During testing, it was observed that some tweets may not resolve or possibly
# even come back with null id values -- possibly a temporary fluke. Workaround.
missing_tweets = []
for (doc_id, in_reply_to_id) in conversation:
    try:
        print [rt for rt in reply_tweets if rt['id'] == in_reply_to_id][0]['text']
    except Exception, e:
        print >> sys.stderr, 'Refetching <<tweet %s>>' % (in_reply_to_id, )
        results = makeTwitterRequest(t.statuses.show, id=in_reply_to_id)
        print results['text']

    # These tweets are already on hand
    print db.get(doc_id)['text']
    print

# <markdowncell>

# Example 5-11. Counting the number of times Twitterers have been retweeted by someone (the_tweet__count_retweets_of_other_users.py)

# <codecell>

# Note: As pointed out in the text, there are now additional/better ways to process retweets
# as the Twitter API has evolved. In particular, take a look at the retweet_count field of the
# status object. See https://dev.twitter.com/docs/platform-objects/tweets. However, the technique
# illustrated in this code is still relevant as some Twitter clients may not follow best practices
# and still use the "RT" or "via" conventions to tweet as opposed to using the Twitter API to issue
# a retweet.

import sys
import couchdb
from couchdb.design import ViewDefinition
from prettytable import PrettyTable

DB = 'tweets-user-timeline-timoreilly' # XXX: IPython Notebook cannot prompt for input
FREQ_THRESHOLD = 3 # XXX: IPython Notebook cannot prompt for input

try:
    server = couchdb.Server('http://localhost:5984')
    db = server[DB]
except couchdb.http.ResourceNotFound, e:
    print """CouchDB database '%s' not found. 
Please check that the database exists and try again.""" % DB
    sys.exit(1)

# Map entities in tweets to the docs that they appear in

def entityCountMapper(doc):
    if doc.get('text'):
        import re
        m = re.search(r"(RT|via)((?:\b\W*@\w+)+)", doc['text'])
        if m:
            entities = m.groups()[1].split()
            for entity in entities:
                yield (entity.lower(), [doc['_id'], doc['id']])
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

# Sorting by value in the client is cheap and easy
# if you're dealing with hundreds or low thousands of tweets

entities_freqs = sorted([(row.key, row.value) for row in
                        db.view('index/retweet_entity_count_by_doc',
                        group=True)], key=lambda x: x[1], reverse=True)

field_names = ['Entity', 'Count']
pt = PrettyTable(field_names=field_names)
pt.align = 'l'

for (entity, freq) in entities_freqs:
    if freq > FREQ_THRESHOLD and entity != '@':
        pt.add_row([entity, freq])

print pt

# <markdowncell>

# Example 5-12. Finding the tweets that have been retweeted most often (the_tweet_count_retweets_by_others.py)

# <codecell>

import sys
import couchdb
from couchdb.design import ViewDefinition
from prettytable import PrettyTable
from twitter__util import pp

DB = 'tweets-user-timeline-timoreilly' # XXX: IPython Notebook cannot prompt for input

try:
    server = couchdb.Server('http://localhost:5984')
    db = server[DB]
except couchdb.http.ResourceNotFound, e:
    print """CouchDB database '%s' not found. 
Please check that the database exists and try again.""" % DB
    sys.exit(1)

# Map entities in tweets to the docs that they appear in

def retweetCountMapper(doc):
    if doc.get('id') and doc.get('text'):
        yield (doc['retweet_count'], 1)

def summingReducer(keys, values, rereduce):
    return sum(values)

view = ViewDefinition('index', 'retweets_by_id', retweetCountMapper, 
                      reduce_fun=summingReducer, language='python')

view.sync(db)

field_names = ['Num Tweets', 'Retweet Count']
pt = PrettyTable(field_names=field_names)
pt.align = 'l'

retweet_total, num_tweets, num_zero_retweets = 0, 0, 0
for (k,v) in sorted([(row.key, row.value) for row in 
                     db.view('index/retweets_by_id', group=True)
                     if row.key is not None],
                 key=lambda x: x[0], reverse=True):
    pt.add_row([k, v])

    if k == "100+":
        retweet_total += 100*v
    elif k == 0:
        num_zero_retweets += v
    else:
        retweet_total += k*v

    num_tweets += v

print pt

print '\n%s of %s authored tweets were retweeted at least once' % \
    (pp(num_tweets - num_zero_retweets), pp(num_tweets),)
print '\t(%s tweet/retweet ratio)\n' % \
      (1.0*(num_tweets - num_zero_retweets)/num_tweets,)

print 'Those %s authored tweets generated %s retweets' % (pp(num_tweets), pp(retweet_total),)

# <markdowncell>

# Example 5-13. Counting hashtag entities in tweets (the_tweet__avg_hashtags_per_tweet.py)

# <codecell>

import sys
import couchdb
from couchdb.design import ViewDefinition

DB = 'tweets-user-timeline-timoreilly' # XXX: IPython Notebook cannot prompt for input

try:
    server = couchdb.Server('http://localhost:5984')
    db = server[DB]
except couchdb.http.ResourceNotFound, e:
    print """CouchDB database '%s' not found. 
Please check that the database exists and try again.""" % DB
    sys.exit(1)

# Emit the number of hashtags in a document

def entityCountMapper(doc):
    if not doc.get('entities'):
        import twitter_text

        def getEntities(tweet):

            # Now extract various entities from it and build up a familiar structure

            extractor = twitter_text.Extractor(tweet['text'])

            # Note that the production Twitter API contains a few additional fields in
            # the entities hash that would require additional API calls to resolve

            entities = {}
            entities['user_mentions'] = []
            for um in extractor.extract_mentioned_screen_names_with_indices():
                entities['user_mentions'].append(um)

            entities['hashtags'] = []
            for ht in extractor.extract_hashtags_with_indices():

                # Massage field name to match production twitter api

                ht['text'] = ht['hashtag']
                del ht['hashtag']
                entities['hashtags'].append(ht)

            entities['urls'] = []
            for url in extractor.extract_urls_with_indices():
                entities['urls'].append(url)

            return entities

        doc['entities'] = getEntities(doc)

    if doc['entities'].get('hashtags'):
        yield (None, len(doc['entities']['hashtags']))


def summingReducer(keys, values, rereduce):
    return sum(values)


view = ViewDefinition('index', 'count_hashtags', entityCountMapper,
                      reduce_fun=summingReducer, language='python')
view.sync(db)

num_hashtags = [row for row in db.view('index/count_hashtags')][0].value

# Now, count the total number of tweets that aren't direct replies

def entityCountMapper(doc):
    if doc.get('text')[0] == '@':
        yield (None, 0)
    else:
        yield (None, 1)


view = ViewDefinition('index', 'num_docs', entityCountMapper,
                      reduce_fun=summingReducer, language='python')
view.sync(db)

num_docs = [row for row in db.view('index/num_docs')][0].value

# Finally, compute the average

print 'Avg number of hashtags per tweet for %s: %s' % \
        (DB.split('-')[-1], 1.0 * num_hashtags / num_docs,)

# <markdowncell>

# Exmaple 5-14. Harvesting tweets for a given query (the_tweet__search.py)

# <codecell>

import sys
import twitter
import couchdb
from couchdb.design import ViewDefinition
from twitter__util import makeTwitterRequest
from twitter__login import login

Q = 'OpenGov' # XXX: IPython Notebook cannot accept input
MAX_PAGES = 5

server = couchdb.Server('http://localhost:5984')
DB = 'search-%s' % (Q.lower().replace('#', '').replace('@', ''), )

t = login()
search_results = t.search.tweets(q=Q, count=100)
tweets = search_results['statuses']

for _ in range(MAX_PAGES-1): # Get more pages
    next_results = search_results['search_metadata']['next_results']

    # Create a dictionary from the query string params
    kwargs = dict([ kv.split('=') for kv in next_results[1:].split("&") ]) 

    search_results = t.search.tweets(**kwargs)
    tweets += search_results['statuses']

    if len(search_results['statuses']) == 0:
        break

    print 'Fetched %i tweets so far' % (len(tweets),)

# Store the data
try:
    db = server.create(DB)
except couchdb.http.PreconditionFailed, e:
    # Already exists, so append to it (but be mindful of appending duplicates with repeat searches.)
    # The refresh_url in the search_metadata or streaming API might also be
    # appropriate to use here.
    db = server[DB]

db.update(tweets, all_or_nothing=True)
print 'Done. Stored data to CouchDB - http://localhost:5984/_utils/database.html?%s' % (DB,)

