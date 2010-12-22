# -*- coding: utf-8 -*-

import sys
import time
import cPickle
import twitter
from twitter__login import login
from twitter__util import makeTwitterRequest 

SCREEN_NAME = sys.argv[1]
FRIENDS_LIMIT = int(sys.argv[2])

# You may need to setup your OAuth settings in twitter__login.py
t = login()

def getFriendIds(screen_name=None, user_id=None, friends_limit=10000):

    ids = []
    cursor = -1
    while cursor != 0:
        params = dict(cursor=cursor)
        if screen_name is not None:
            params['screen_name'] = screen_name
        else:
            params['user_id'] = user_id

        response = makeTwitterRequest(t, t.friends.ids, **params)

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
