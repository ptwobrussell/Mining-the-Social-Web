# -*- coding: utf-8 -*-

# Build up a digraph where an edge exists between two users if the source node is following the destination node

import sys
import json
import networkx as nx
import redis

SCREEN_NAME = sys.argv[1]


def getRedisIdByScreenName(screen_name, key_name):
    return 'screen_name$' + screen_name + '$' + key_name


def getRedisIdByUserId(user_id, key_name):
    return 'user_id$' + str(user_id) + '$' + key_name


g = nx.Graph()
r = redis.Redis()

# Compute all ids for nodes appearing in the graph

friend_ids = list(r.smembers(getRedisIdByScreenName(SCREEN_NAME, 'friend_ids')))
id_for_screen_name = json.loads(r.get(getRedisIdByScreenName(SCREEN_NAME,
                                'info.json')))['id']
ids = [id_for_screen_name] + friend_ids

for current_id in ids:
    print 'Processing', current_id

    try:
        current_info = json.loads(r.get(getRedisIdByUserId(current_id, 'info.json'
                                  )))
        current_screen_name = current_info['screen_name']
        friend_ids = list(r.smembers(getRedisIdByScreenName(current_screen_name,
                          'friend_ids')))

        # filter out ids for this person if they aren't also SCREEN_NAME's friends too, which is the basis of the query

        friend_ids = [fid for fid in friend_ids if fid in ids]
    except Exception, e:
        print 'Skipping', current_id

    for friend_id in friend_ids:
        try:
            friend_info = json.loads(r.get(getRedisIdByUserId(friend_id,
                                     'info.json')))
        except TypeError, e:
            print '\tSkipping', friend_id, 'for', current_screen_name
            continue

        g.add_edge(current_screen_name, friend_info['screen_name'])

# store graph to disk by pickling it...

nx.write_gpickle(g, SCREEN_NAME + '.gpickle')

# you can read it back out like this...
# g = nx.read_gpickle(SCREEN_NAME + '.gpickle')
