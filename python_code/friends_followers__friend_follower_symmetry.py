# -*- coding: utf-8 -*-

import sys
import locale
import time
import functools
import twitter
from twitter.oauth_dance import oauth_dance
import redis

MAXINT = sys.maxint
locale.setlocale(locale.LC_ALL, '')  # for nice number formatting

SCREEN_NAME = sys.argv[1]

# Go to http://twitter.com/apps/new to create an app 
# to get the consumer key/secret

CONSUMER_KEY = sys.argv[2]
CONSUMER_SECRET = sys.argv[3]

(oauth_token, oauth_token_secret) = oauth_dance('MiningTheSocialWeb',
        CONSUMER_KEY, CONSUMER_SECRET)
t = twitter.Twitter(domain='api.twitter.com', api_version='1',
                    auth=twitter.oauth.OAuth(oauth_token, oauth_token_secret,
                    CONSUMER_KEY, CONSUMER_SECRET))

r = redis.Redis()  # connect using default settings for localhost

# A template-like function that can get friends or followers depending on
# the function passed into it via func.

def _getFriendsOrFollowersUsingFunc(
    func,
    key_name,
    screen_name=None,
    limit=10000,
    ):

    wait_period = 2  # secs
    cursor = -1

    while cursor != 0:
        if wait_period > 3600:  # 1 hour
            print >> sys.stderr, 'Too many retries. Exiting'
            exit()

        try:
            response = func(screen_name=screen_name, cursor=cursor)
            for _id in response['ids']:
                r.sadd(getRedisIdByScreenName(screen_name, key_name), _id)
            wait_period = 2
        except twitter.api.TwitterHTTPError, e:
            if e.e.code == 401:
                print >> sys.stderr, 'Encountered 401 Error (Not Authorized)'
                print 'User %s is protecting their tweets' % (screen_name, )
            elif e.e.code in (502, 503):
                print >> sys.stderr, \
                    'Encountered %i Error. Trying again in %i seconds' \
                    % (e.e.code, wait_period)
                time.sleep(wait_period)
                wait_period *= 1.5
                continue
            elif t.account.rate_limit_status()['remaining_hits'] == 0:
                status = t.account.rate_limit_status()
                now = time.time()  # UTC
                when_rate_limit_resets = status['reset_time_in_seconds']  # UTC
                sleep_time = when_rate_limit_resets - now
                print >> sys.stderr, \
                    'Rate limit reached: sleeping for %i secs (%i mins)' \
                    % (sleep_time, sleep_time / 60)
                time.sleep(sleep_time)
                continue
            else:
                raise e # Best to handle this based on the specific issue

        cursor = response['next_cursor']
        scard = r.scard(getRedisIdByScreenName(screen_name, key_name))
        print >> sys.stderr, 'Fetched %s ids for %s' % (scard, screen_name)
        if scard >= limit:
            break

# A convenience function

def getRedisIdByScreenName(screen_name, key_name):
    return 'screen_name$' + screen_name + '$' + key_name


# Some wrappers around _getFriendsOrFollowersUsingFunc that bind the first two arguments

getFriends = functools.partial(_getFriendsOrFollowersUsingFunc, t.friends.ids,
                               'friend_ids')
getFollowers = functools.partial(_getFriendsOrFollowersUsingFunc,
                                 t.followers.ids, 'follower_ids')

# Get the data

print >> sys.stderr, 'Getting friends for %s...' % (SCREEN_NAME, )
getFriends(SCREEN_NAME, limit=MAXINT)

print >> sys.stderr, 'Getting followers for %s...' % (SCREEN_NAME, )
getFollowers(SCREEN_NAME, limit=MAXINT)

# Use Redis to compute the numbers

n_friends = r.scard(getRedisIdByScreenName(SCREEN_NAME, 'friend_ids'))

n_followers = r.scard(getRedisIdByScreenName(SCREEN_NAME, 'follower_ids'))

n_friends_diff_followers = \
    r.sdiffstore('temp', 
                 [getRedisIdByScreenName(SCREEN_NAME, 'friend_ids'),
                 getRedisIdByScreenName(SCREEN_NAME,'follower_ids')])
r.delete('temp')

n_followers_diff_friends = \
    r.sdiffstore('temp',
                 [getRedisIdByScreenName(SCREEN_NAME, 'follower_ids'),
                 getRedisIdByScreenName(SCREEN_NAME, 'friend_ids')])
r.delete('temp')

n_friends_inter_followers = \
    r.sinterstore('temp', 
                  [getRedisIdByScreenName(SCREEN_NAME, 'follower_ids'),
                  getRedisIdByScreenName(SCREEN_NAME, 'friend_ids')])
r.delete('temp')

print '%s is following %s' % (SCREEN_NAME, locale.format('%d', n_friends, True))

print '%s is being followed by %s' % (SCREEN_NAME, locale.format('%d',
                                      n_followers, True))

print '%s of %s are not following %s back' % (locale.format('%d',
        n_friends_diff_followers, True), locale.format('%d', n_friends, True),
        SCREEN_NAME)

print '%s of %s are not being followed back by %s' % (locale.format('%d',
        n_followers_diff_friends, True), locale.format('%d', n_followers, True),
        SCREEN_NAME)

print '%s has %s mutual friends (followers who are also being followed)' \
    % (SCREEN_NAME, locale.format('%d', n_friends_inter_followers, True))
