# -*- coding: utf-8 -*-

import sys
import time
import twitter
from twitter.oauth_dance import oauth_dance
import couchdb
from couchdb.design import ViewDefinition


def usage():
    print 'Usage: $ %s timeline_name [max_pages] [user]' % (sys.argv[0], )
    print
    print '\ttimeline_name in [public, home, user]'
    print '\t0 < max_pages <= 16 for timeline_name in [home, user]'
    print '\tmax_pages == 1 for timeline_name == public'
    print 'Notes:'
    print '\t* ~800 statuses are available from the home timeline.'
    print '\t* ~3200 statuses are available from the user timeline.'
    print '\t* The public timeline updates once every 60 secs and returns 20 statuses.'
    print '\t* See the streaming/search API for additional options to harvest tweets.'

    exit()


if len(sys.argv) < 2 or sys.argv[1] not in ('public', 'home', 'user'):
    usage()
if len(sys.argv) > 2 and not sys.argv[2].isdigit():
    usage()
if len(sys.argv) > 3 and sys.argv[1] != 'user':
    usage()

TIMELINE_NAME = sys.argv[1]
MAX_PAGES = int(sys.argv[2])
USER = None
KW = {  # For the Twitter API call
    'count': 200,
    'skip_users': 'true',
    'include_entities': 'true',
    'since_id': 1,
    }
if TIMELINE_NAME == 'user':
    USER = sys.argv[3]
    KW['id'] = USER  # id or screen name
if TIMELINE_NAME == 'home' and MAX_PAGES > 4:
    MAX_PAGES = 4
if TIMELINE_NAME == 'user' and MAX_PAGES > 16:
    MAX_PAGES = 16
if TIMELINE_NAME == 'public':
    MAX_PAGES = 1

# Go to http://twitter.com/apps/new to create an app and get these items

consumer_key = ''
consumer_secret = ''

# authenticate with the twitter api

(oauth_token, oauth_token_secret) = oauth_dance('MiningTheSocialWeb',
        consumer_key, consumer_secret)

t = twitter.Twitter(domain='api.twitter.com', api_version='1',
                    auth=twitter.oauth.OAuth(oauth_token, oauth_token_secret,
                    consumer_key, consumer_secret))

# establish a connection to a couchdb database

server = couchdb.Server('http://localhost:5984')
DB = 'tweets-%s-timeline' % (TIMELINE_NAME, )
if USER:
    DB = '%s-%s' % (DB, USER)

try:
    db = server.create(DB)
except couchdb.http.PreconditionFailed, e:

    # already exists, so append to it, keeping in mind that duplicates could occur

    db = server[DB]

    # Try to avoid appending duplicate data into the system by only retrieving tweets 
    # newer than the ones already in the system. A trivial mapper/reducer combination 
    # allows us to pull out the max tweet id which guards against duplicates for the 
    # home and user timelines. It has no effect for the public timeline


    def idMapper(doc):
        yield (None, doc['id'])


    def maxFindingReducer(keys, values, rereduce):
        return max(values)


    view = ViewDefinition('index', 'max_tweet_id', idMapper, maxFindingReducer,
                          language='python')
    view.sync(db)
    KW['since_id'] = int([_id for _id in db.view('index/max_tweet_id')][0].value)

# Encapsulate common error handling - introduced in chapter 3


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


# Harvest tweets for the given timeline.
# For friend and home timelines, the unofficial limitation is about 800 statuses although
# other documentation may state otherwise. The public timeline only returns 20 statuses 
# and gets updated every 60 seconds.
# See http://groups.google.com/group/twitter-development-talk/browse_thread/thread/4678df70c301be43
# Note that the count and since_id params have no effect for the public timeline

page_num = 1
wait_period = 2
while page_num <= MAX_PAGES:
    while True:
        try:
            api_call = getattr(t.statuses, TIMELINE_NAME + '_timeline')
            KW['page'] = page_num
            tweets = api_call(**KW)
            db.update(tweets, all_or_nothing=True)
            print 'Fetched %i tweets' % len(tweets)
            wait_period = 2
            break
        except twitter.api.TwitterHTTPError, e:
            wait_period = handleTwitterHTTPError(e, wait_period)
            if wait_period is None:
                break
    page_num += 1
