# -*- coding: utf-8 -*-

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

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print >> sys.stderr, "Please supply at least two screen names."
        sys.exit(1)

    # Note:
    # The assumption is that the screen names you are 
    # supplying have already been added to Redis.
    # See friends_followers__get_friends__refactored.py

    friendsFollowersInCommon(sys.argv[1:])
