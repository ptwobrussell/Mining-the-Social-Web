# -*- coding: utf-8 -*-

import sys
import json
import redis
from twitter__login import login

# A makeTwitterRequest call through to the /users/lookup 
# resource, which accepts a comma separated list of up 
# to 100 screen names. Details are fairly uninteresting. 
# See also http://dev.twitter.com/doc/get/users/lookup
from twitter__util import getUserInfo

if __name__ == "__main__":
    screen_names = sys.argv[1:]

    t = login()
    r = redis.Redis()

    print json.dumps(
            getUserInfo(t, r, screen_names=screen_names),
            indent=4
          )
