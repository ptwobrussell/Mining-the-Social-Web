# -*- coding: utf-8 -*-

import sys
import json
import locale
import redis

SCREEN_NAME = sys.argv[1]

locale.setlocale(locale.LC_ALL, '')


def pp(_int):  # for nice number formatting
    return locale.format('%d', _int, True)


def getRedisIdByScreenName(screen_name, key_name):
    return 'screen_name$' + screen_name + '$' + key_name


def getRedisIdByUserId(user_id, key_name):
    return 'user_id$' + str(user_id) + '$' + key_name


def calculate():
    r = redis.Redis()  # default connection settings on localhost

    screen_name = SCREEN_NAME

    follower_ids = list(r.smembers(getRedisIdByScreenName(screen_name,
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

    r.set(getRedisIdByScreenName(screen_name, 'follower_freqs'),
          json.dumps(freqs))

    keys = freqs.keys()
    keys.sort()

    print 'The top 10 followers from the sample:'

    for (user, freq) in reversed([(user['screen_name'], k) for k in keys[-10:]
                                 for user in freqs[k]]):
        print user, pp(freq)

    all_freqs = [k for k in keys for user in freqs[k]]
    avg = reduce(lambda x, y: x + y, all_freqs) / len(all_freqs)
    print "The average number of followers for %s's followers: %s" \
        % (screen_name, pp(avg))


# psyco can only compile functions, so wrap code in a function

try:
    import psyco
    psyco.bind(calculate)
except ImportError, e:
    pass  # psyco not installed

calculate()
