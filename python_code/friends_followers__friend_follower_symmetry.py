# -*- coding: utf-8 -*-

import sys
import locale
import time
import functools
import twitter
from twitter.oauth_dance import oauth_dance
import redis

SCREEN_NAME = sys.argv[1]

MAXINT = sys.maxint

locale.setlocale(locale.LC_ALL, '')  # for nice number formatting

# Go to http://twitter.com/apps/new to create an app and get these items

consumer_key = ''
consumer_secret = ''

(oauth_token, oauth_token_secret) = oauth_dance("Your application's name",
        consumer_key, consumer_secret)
t = twitter.Twitter(domain='api.twitter.com', api_version='1',
                    auth=twitter.oauth.OAuth(oauth_token, oauth_token_secret,
                    consumer_key, consumer_secret))
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
            print 'Too many retries. Exiting'
            exit()

        try:
            response = func(screen_name=screen_name, cursor=cursor)
            for _id in response['ids']:
                r.sadd(getRedisIdByScreenName(screen_name, key_name), _id)
            wait_period = 2
        except twitter.api.TwitterHTTPError, e:
            if e.e.code == 401:
                print 'Encountered 401 Error (Not Authorized)'
                print 'User %s is protecting their tweets' % (screen_name, )
            elif e.e.code in (502, 503):
                print 'Encountered %i Error. Trying again in %i seconds' \
                    % (e.e.code, wait_period)
                time.sleep(wait_period)
                wait_period *= 1.5
                continue
            elif t.account.rate_limit_status()['remaining_hits'] == 0:
                status = t.account.rate_limit_status()
                now = time.time()  # UTC
                when_rate_limit_resets = status['reset_time_in_seconds']  # UTC
                sleep_time = when_rate_limit_resets - now
                print 'Rate limit reached: sleeping for %i secs (%i mins)' \
                    % (sleep_time, sleep_time / 60)
                time.sleep(sleep_time)
                continue
            else:
                raise e # Best to handle this based on the specific issue


        cursor = response['next_cursor']
        scard = r.scard(getRedisIdByScreenName(screen_name, key_name))
        print 'Fetched %s ids for %s' % (scard, screen_name)
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

screen_name = SCREEN_NAME

# get the data

print 'Getting friends for %s...' % (screen_name, )
getFriends(screen_name, limit=MAXINT)
print 'Getting followers for %s...' % (screen_name, )
getFollowers(screen_name, limit=MAXINT)

# use redis to compute the numbers

n_friends = r.scard(getRedisIdByScreenName(screen_name, 'friend_ids'))
n_followers = r.scard(getRedisIdByScreenName(screen_name, 'follower_ids'))
n_friends_diff_followers = r.sdiffstore('temp',
                                        [getRedisIdByScreenName(screen_name,
                                        'friend_ids'),
                                        getRedisIdByScreenName(screen_name,
                                        'follower_ids')])
r.delete('temp')
n_followers_diff_friends = r.sdiffstore('temp',
                                        [getRedisIdByScreenName(screen_name,
                                        'follower_ids'),
                                        getRedisIdByScreenName(screen_name,
                                        'friend_ids')])
r.delete('temp')
n_friends_inter_followers = r.sinterstore('temp',
        [getRedisIdByScreenName(screen_name, 'follower_ids'),
        getRedisIdByScreenName(screen_name, 'friend_ids')])
r.delete('temp')

print '-' * 50
print '%s is following %s' % (screen_name, locale.format('%d', n_friends, True))
print '%s is being followed by %s' % (screen_name, locale.format('%d',
                                      n_followers, True))
print '%s of %s are not following %s back' % (locale.format('%d',
        n_friends_diff_followers, True), locale.format('%d', n_followers, True),
        screen_name)
print '%s of %s are not being followed back by %s' % (locale.format('%d',
        n_followers_diff_friends, True), locale.format('%d', n_followers, True),
        screen_name)
print '%s has %s mutual friends (followers who are also being followed)' \
    % (screen_name, locale.format('%d', n_friends_inter_followers, True))
print '-' * 50
