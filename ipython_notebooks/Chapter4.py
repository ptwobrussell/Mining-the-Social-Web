# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <markdowncell>

# #Mining the Social Web, 1st Edition - Friends, Followers, and Setwise Operations (Chapter 4)
# 
# If you only have 10 seconds...
# 
# Twitter's new API will prevent you from running much of the code from _Mining the Social Web_, and this IPython Notebook shows you how to roll with the changes and adapt as painlessly as possible until an updated printing is available. In particular, it shows you how to authenticate before executing any API requests illustrated in this chapter. It is highly recommended that you read the IPython Notebook file for Chapter 1 before attempting the examples in this chapter if you haven't already.
# 
# If you have a couple of minutes...
# 
# Twitter is officially retiring v1.0 of their API as of March 2013 with v1.1 of the API being the new status quo. There are a few fundamental differences that social web miners that should consider (see Twitter's blog at https://dev.twitter.com/blog/changes-coming-to-twitter-api and https://dev.twitter.com/docs/api/1.1/overview) with the two changes that are most likely to affect an existing workflow being that authentication is now mandatory for *all* requests, rate-limiting being on a per resource basis (as opposed to an overall rate limit based on a fixed number of requests per unit time), various platform objects changing (for the better), and search semantics changing to a "pageless" approach. All in all, the v1.1 API looks much cleaner and more consistent, and it should be a good thing longer-term although it may cause interim pains for folks migrating to it.
# 
# The latest printing of Mining the Social Web (2012-02-22, Third release) reflects v1.0 of the API, and this document is intended to provide readers with updated examples from Chapter 4 of the book until a new printing provides updates.
# 
# Unlike the IPython Notebook for Chapter 1, there is no filler in this notebook at this time. See the Chapter 1 notebook for a good introduction to using the Twitter API and all that it entails.
# 
# I'm working through updates to the sample source code for the remaining Twitter-related chapter (Chapter 5) and expect to have the GitHub repository updated by the end of March 2013. Thank you for your patience while I get this all sorted out. As a reader of my book, I want you to know that I'm committed to helping you in any way that I can, so please reach out on Facebook at https://www.facebook.com/MiningTheSocialWeb or on Twitter at http://twitter.com/SocialWebMining if you have any questions or concerns in the meanwhile. I'd also love your feedback on whether or not you think that IPython Notebook is a good tool for tinkering with the source code for the book, because I'm strongly considering it as a supplement for each chapter.
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
# * Arguments that are typically passed in through the command line are hardcoded in the examples for convenience. CLI arguments are typically in ALL_CAPS, so they're easy to spot and change as needed.
# 
# * For simplicity, examples that harvest data are limited to small numbers so that it's easier to use experiment with this notebook (given that @timoreilly, the principal subject of the examples, has vast numbers of followers.)
# 
# * The parenthetical file names at the end of the captions for the examples correspond to files in the 'python_code' folder of the GitHub repository
# 
# * Just like you'd learn from reading the book, you'll need to have a Redis server running because several of the examples in this chapter store and fetch data from it.

# <markdowncell>

# Example 4-1. Fetching extended information about a Twitter user

# <codecell>

import twitter
import json

# Go to http://twitter.com/apps/new to create an app and get these items
# See https://dev.twitter.com/docs/auth/oauth for more information on Twitter's OAuth implementation

CONSUMER_KEY = ''
CONSUMER_SECRET = ''
OAUTH_TOKEN = ''
OAUTH_TOKEN_SECRET = ''

auth = twitter.oauth.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET,
                           CONSUMER_KEY, CONSUMER_SECRET)

t = twitter.Twitter(domain='api.twitter.com', 
                              api_version='1.1',
                              auth=auth
                             )

screen_name = 'timoreilly'

response = t.users.show(screen_name=screen_name)
print json.dumps(response, sort_keys=True, indent=4)

# <markdowncell>

# Example 4-2. Using OAuth to authenticate and grab some friend data (friends__followers_get_friends.py)

# <codecell>

import sys
import time
import cPickle
import twitter

SCREEN_NAME = 'timoreilly' # XXX: IPython Notebook cannot prompt for input

friends_limit = 10000

ids = []
wait_period = 2  # secs
cursor = -1

while cursor != 0:
    if wait_period > 3600:  # 1 hour
        print >> sys.stderr, 'Too many retries. Saving partial data to disk and exiting'
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

# <markdowncell>

# Example 4-3. Example 4-2 refactored to use two common utilties for OAuth and making API requests (friends_followers__get_friends_refactored.py)

# <codecell>

import sys
import time
import cPickle
import twitter
from twitter__util import makeTwitterRequest 

SCREEN_NAME = 'timoreilly' # XXX: IPython Notebook cannot prompt for input
FRIENDS_LIMIT = 10000 # XXX: IPython Notebook cannot prompt for input

def getFriendIds(screen_name=None, user_id=None, friends_limit=10000):

    ids = []
    cursor = -1
    while cursor != 0:
        params = dict(cursor=cursor)
        if screen_name is not None:
            params['screen_name'] = screen_name
        else:
            params['user_id'] = user_id

        response = makeTwitterRequest(t.friends.ids, **params)

        ids.extend(response['ids'])
        cursor = response['next_cursor']
        print >> sys.stderr, \
            'Fetched %i ids for %s' % (len(ids), screen_name or user_id)
        if len(ids) >= friends_limit:
            break

    return ids

if __name__ == '__main__':
    ids = getFriendIds(SCREEN_NAME, friends_limit=FRIENDS_LIMIT)

    # do something interesting with the ids

    print ids

# <markdowncell>

# Example 4-4. Harvesting, storing, and computing statistics about friends and followers (friends_followers__friend_follower_symmetry.py)

# <codecell>

import sys
import locale
import time
import functools
import twitter
import redis

# A template-like function for maximizing code reuse,
# which is essentially a wrapper around makeTwitterRequest
# with some additional logic in place for interfacing with 
# Redis
from twitter__util import _getFriendsOrFollowersUsingFunc

# Creates a consistent key value for a user given a screen name
from twitter__util import getRedisIdByScreenName

SCREEN_NAME = 'timoreilly' # XXX: IPython Notebook cannot prompt for input

MAXINT = 10000 #sys.maxint

# For nice number formatting
locale.setlocale(locale.LC_ALL, '')  

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

# <markdowncell>

# Example 4-5. Resolving basic user information such as screen names from IDs (friends_followers__get_user_info.py)

# <codecell>

import sys
import json
import redis

# A makeTwitterRequest call through to the /users/lookup 
# resource, which accepts a comma separated list of up 
# to 100 screen names. Details are fairly uninteresting. 
# See also http://dev.twitter.com/doc/get/users/lookup
from twitter__util import getUserInfo

if __name__ == "__main__":
    # XXX: IPython Notebook cannot prompt for input
    screen_names = ['timoreilly', 'socialwebmining', 'ptwobrussell']

    r = redis.Redis()

    print json.dumps(
            getUserInfo(t, r, screen_names=screen_names),
            indent=4
          )

# <markdowncell>

# Example 4-7. Finding common friends/followers for multiple Twitterers, with output that's easier on the eyes (friends_followers__friends_followers_in_common.py)

# <codecell>

import sys
import redis

from twitter__util import getRedisIdByScreenName

# A pretty-print function for numbers
from twitter__util import pp

r = redis.Redis()

def friendsFollowersInCommon(screen_names):
    r.sinterstore('temp$friends_in_common', 
                  [getRedisIdByScreenName(screen_name, 'friend_ids') 
                      for screen_name in screen_names]
                 )

    r.sinterstore('temp$followers_in_common',
                  [getRedisIdByScreenName(screen_name, 'follower_ids')
                      for screen_name in screen_names]
                 )

    print 'Friends in common for %s: %s' % (', '.join(screen_names),
            pp(r.scard('temp$friends_in_common')))

    print 'Followers in common for %s: %s' % (', '.join(screen_names),
            pp(r.scard('temp$followers_in_common')))

    # Clean up scratch workspace

    r.delete('temp$friends_in_common')
    r.delete('temp$followers_in_common')

# Note:
# The assumption is that the screen names you are 
# supplying have already been added to Redis.
# See friends_followers__get_friends__refactored.py (Example 4-3)

# XXX: IPython Notebook cannot prompt for input
friendsFollowersInCommon(['timoreilly', 'socialwebmining'])

# <markdowncell>

# Example 4-8. Crawling friends/followers connections (friends_followers__crawl.py)

# <codecell>

import sys
import redis
import functools
from twitter__util import getUserInfo
from twitter__util import _getFriendsOrFollowersUsingFunc

SCREEN_NAME = 'timoreilly' # XXX: IPython Notebook cannot prompt for input

r = redis.Redis()

# Some wrappers around _getFriendsOrFollowersUsingFunc that 
# create convenience functions

getFriends = functools.partial(_getFriendsOrFollowersUsingFunc, 
                               t.friends.ids, 'friend_ids', t, r)
getFollowers = functools.partial(_getFriendsOrFollowersUsingFunc,
                                 t.followers.ids, 'follower_ids', t, r)

def crawl(
    screen_names,
    friends_limit=10000,
    followers_limit=10000,
    depth=1,
    friends_sample=0.2, #XXX
    followers_sample=0.0,
    ):

    getUserInfo(t, r, screen_names=screen_names)
    for screen_name in screen_names:
        friend_ids = getFriends(screen_name, limit=friends_limit)
        follower_ids = getFollowers(screen_name, limit=followers_limit)

        friends_info = getUserInfo(t, r, user_ids=friend_ids, 
                                   sample=friends_sample)

        followers_info = getUserInfo(t, r, user_ids=follower_ids,
                                     sample=followers_sample)

        next_queue = [u['screen_name'] for u in friends_info + followers_info]

        d = 1
        while d < depth:
            d += 1
            (queue, next_queue) = (next_queue, [])
            for _screen_name in queue:
                friend_ids = getFriends(_screen_name, limit=friends_limit)
                follower_ids = getFollowers(_screen_name, limit=followers_limit)

                next_queue.extend(friend_ids + follower_ids)

                # Note that this function takes a kw between 0.0 and 1.0 called
                # sample that allows you to crawl only a random sample of nodes
                # at any given level of the graph

                getUserInfo(t, r, user_ids=next_queue)

crawl([SCREEN_NAME])

# The data is now in the system. Do something interesting. For example, 
# find someone's most popular followers as an indiactor of potential influence.
# See friends_followers__calculate_avg_influence_of_followers.py

# <markdowncell>

# Example 4-9. Calculating a Twitterer's most popular followers (friends_followers__calculate_avg_influence_of_followers.py)

# <codecell>

import sys
import json
import locale
import redis
from prettytable import PrettyTable

# Pretty printing numbers
from twitter__util import pp 

# These functions create consistent keys from 
# screen names and user id values
from twitter__util import getRedisIdByScreenName 
from twitter__util import getRedisIdByUserId

SCREEN_NAME = 'timoreilly' # XXX: IPython Notebook cannot prompt for input

locale.setlocale(locale.LC_ALL, '')

def calculate():
    r = redis.Redis()  # Default connection settings on localhost

    follower_ids = list(r.smembers(getRedisIdByScreenName(SCREEN_NAME,
                        'follower_ids')))

    followers = r.mget([getRedisIdByUserId(follower_id, 'info.json')
                       for follower_id in follower_ids])
    followers = [json.loads(f) for f in followers if f is not None]

    freqs = {}
    for f in followers:
        cnt = f['followers_count']
        if not freqs.has_key(cnt):
            freqs[cnt] = []

        freqs[cnt].append({'screen_name': f['screen_name'], 'user_id': f['id']})

    # It could take a few minutes to calculate freqs, so store a snapshot for later use

    r.set(getRedisIdByScreenName(SCREEN_NAME, 'follower_freqs'),
          json.dumps(freqs))

    keys = freqs.keys()
    keys.sort()

    print 'The top 10 followers from the sample:'

    field_names = ['Date', 'Count']
    pt = PrettyTable(field_names=field_names)
    pt.align = 'l'

    for (user, freq) in reversed([(user['screen_name'], k) for k in keys[-10:]
                                    for user in freqs[k]]):
        pt.add_row([user, pp(freq)])

    print pt

    all_freqs = [k for k in keys for user in freqs[k]]
    avg = reduce(lambda x, y: x + y, all_freqs) / len(all_freqs)

    print "\nThe average number of followers for %s's followers: %s" \
        % (SCREEN_NAME, pp(avg))

calculate()

# <markdowncell>

# Example 4-10. Exporting friend/follower data from Redis to NetworkX for easy graph analytics (friends_followers__redis_to_networkx.py)

# <codecell>

# Summary: Build up a digraph where an edge exists between two users 
# if the source node is following the destination node

import os
import sys
import json
import networkx as nx
import redis

from twitter__util import getRedisIdByScreenName
from twitter__util import getRedisIdByUserId

SCREEN_NAME = 'timoreilly' # XXX: IPython Notebook cannot prompt for input

g = nx.Graph()
r = redis.Redis()

# Compute all ids for nodes appearing in the graph

friend_ids = list(r.smembers(getRedisIdByScreenName(SCREEN_NAME, 'friend_ids')))
id_for_screen_name = json.loads(r.get(getRedisIdByScreenName(SCREEN_NAME,
                                'info.json')))['id']
ids = [id_for_screen_name] + friend_ids

for current_id in ids:
    print >> sys.stderr, 'Processing user with id', current_id

    try:
        current_info = json.loads(r.get(getRedisIdByUserId(current_id, 'info.json'
                                  )))
        current_screen_name = current_info['screen_name']
        friend_ids = list(r.smembers(getRedisIdByScreenName(current_screen_name,
                          'friend_ids')))

        # filter out ids for this person if they aren't also SCREEN_NAME's friends too, 
        # which is the basis of the query

        friend_ids = [fid for fid in friend_ids if fid in ids]
    except Exception, e:
        print >> sys.stderr, 'Skipping', current_id

    for friend_id in friend_ids:
        try:
            friend_info = json.loads(r.get(getRedisIdByUserId(friend_id,
                                     'info.json')))
        except TypeError, e:
            print >> sys.stderr, '\tSkipping', friend_id, 'for', current_screen_name
            continue

        g.add_edge(current_screen_name, friend_info['screen_name'])

# Pickle the graph to disk...

if not os.path.isdir('out'):
    os.mkdir('out')

filename = os.path.join('out', SCREEN_NAME + '.gpickle')
nx.write_gpickle(g, filename)

print 'Pickle file stored in: %s' % filename

# You can un-pickle like so...

# g = nx.read_gpickle(os.path.join('out', SCREEN_NAME + '.gpickle'))

# <markdowncell>

# Example 4-11. Using NetworkX to find cliques in graphs (friends_followers__clique_analysis.py)

# <codecell>

import sys
import json
import networkx as nx

G = 'out/timoreilly.gpickle' # IPython Notebook cannot prompt for input

g = nx.read_gpickle(G)

# Finding cliques is a hard problem, so this could
# take a while for large graphs.
# See http://en.wikipedia.org/wiki/NP-complete and 
# http://en.wikipedia.org/wiki/Clique_problem

cliques = [c for c in nx.find_cliques(g)]

num_cliques = len(cliques)

clique_sizes = [len(c) for c in cliques]
max_clique_size = max(clique_sizes)
avg_clique_size = sum(clique_sizes) / num_cliques

max_cliques = [c for c in cliques if len(c) == max_clique_size]

num_max_cliques = len(max_cliques)

max_clique_sets = [set(c) for c in max_cliques]
people_in_every_max_clique = list(reduce(lambda x, y: x.intersection(y),
                                  max_clique_sets))

print 'Num cliques:', num_cliques
print 'Avg clique size:', avg_clique_size
print 'Max clique size:', max_clique_size
print 'Num max cliques:', num_max_cliques
print
print 'People in all max cliques:'
print json.dumps(people_in_every_max_clique, indent=4)
print
print 'Max cliques:'
print json.dumps(max_cliques, indent=4)

