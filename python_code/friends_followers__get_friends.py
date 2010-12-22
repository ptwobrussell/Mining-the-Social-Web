# -*- coding: utf-8 -*-

import sys
import time
import cPickle
import twitter
from twitter.oauth_dance import oauth_dance

SCREEN_NAME = sys.argv[1]

# Go to http://twitter.com/apps/new to create an app 
# to get the consumer key/secret

CONSUMER_KEY = sys.argv[2]
CONSUMER_SECRET = sys.argv[3]

friends_limit = 10000

(oauth_token, oauth_token_secret) = oauth_dance('MiningTheSocialWeb',
        CONSUMER_KEY, CONSUMER_SECRET)
t = twitter.Twitter(domain='api.twitter.com', api_version='1',
                    auth=twitter.oauth.OAuth(oauth_token, oauth_token_secret,
                    CONSUMER_KEY, CONSUMER_SECRET))

ids = []
wait_period = 2  # secs
cursor = -1

while cursor != 0:
    if wait_period > 3600:  # 1 hour
        print >> sys.stderr, \
            'Too many retries. Saving partial data to disk and exiting'
        f = file('%s.friend_ids' % str(cursor), 'wb')
        cPickle.dump(ids, f)
        f.close()
        exit()

    try:
        response = t.friends.ids(screen_name=SCREEN_NAME, cursor=cursor)
        ids.extend(response['ids'])
        wait_period = 2
    except twitter.api.TwitterHTTPError, e:
        if e.e.code == 401:
            print >> sys.stderr, 'Encountered 401 Error (Not Authorized)'
            print >> sys.stderr, 'User %s is protecting their tweets' % (SCREEN_NAME, )
        elif e.e.code in (502, 503):
            print >> sys.stderr, \
                'Encountered %i Error. Trying again in %i seconds' % \
                (e.e.code, wait_period)
            time.sleep(wait_period)
            wait_period *= 1.5
            continue
        elif t.account.rate_limit_status()['remaining_hits'] == 0:
            status = t.account.rate_limit_status()
            now = time.time()  # UTC
            when_rate_limit_resets = status['reset_time_in_seconds']  # UTC
            sleep_time = when_rate_limit_resets - now
            print >> sys.stderr, \
                'Rate limit reached. Trying again in %i seconds' % (sleep_time,)
            time.sleep(sleep_time)
            continue
        else:
            raise e # Best to handle this on a case by case basis

    cursor = response['next_cursor']
    print >> sys.stderr, 'Fetched %i ids for %s' % (len(ids), SCREEN_NAME)
    if len(ids) >= friends_limit:
        break

# Do something interesting with the ids

print ids
