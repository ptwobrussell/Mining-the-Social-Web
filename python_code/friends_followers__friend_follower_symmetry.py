# -*- coding: utf-8 -*-

import sys
import locale
import time
import functools
import twitter
import redis
from twitter__login import login

# A template-like function for maximizing code reuse,
# which is essentially a wrapper around makeTwitterRequest
# with some additional logic in place for interfacing with 
# Redis
from twitter__util import _getFriendsOrFollowersUsingFunc

# Creates a consistent key value for a user given a screen name
from twitter__util import getRedisIdByScreenName

SCREEN_NAME = sys.argv[1]

MAXINT = sys.maxint

# For nice number formatting
locale.setlocale(locale.LC_ALL, '')  

# You may need to setup your OAuth settings in twitter__login.py

t = login()

# Connect using default settings for localhost
r = redis.Redis()  

# Some wrappers around _getFriendsOrFollowersUsingFunc 
# that bind the first two arguments

getFriends = functools.partial(_getFriendsOrFollowersUsingFunc, 
                               t.friends.ids, 'friend_ids', t, r)

getFollowers = functools.partial(_getFriendsOrFollowersUsingFunc,
                                 t.followers.ids, 'follower_ids', t, r)

screen_name = SCREEN_NAME

# get the data

print >> sys.stderr, 'Getting friends for %s...' % (screen_name, )
getFriends(screen_name, limit=MAXINT)

print >> sys.stderr, 'Getting followers for %s...' % (screen_name, )
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

print '%s is following %s' % (screen_name, locale.format('%d', n_friends, True))
print '%s is being followed by %s' % (screen_name, locale.format('%d',
                                      n_followers, True))
print '%s of %s are not following %s back' % (locale.format('%d',
        n_friends_diff_followers, True), locale.format('%d', n_friends, True),
        screen_name)
print '%s of %s are not being followed back by %s' % (locale.format('%d',
        n_followers_diff_friends, True), locale.format('%d', n_followers, True),
        screen_name)
print '%s has %s mutual friends' \
    % (screen_name, locale.format('%d', n_friends_inter_followers, True))
