# -*- coding: utf-8 -*-

import sys
import urllib2
import json
import redis

SCREEN_NAME = sys.argv[1]
API_KEY = sys.argv[2]
API_ENDPOINT = \
    'http://api.infochimps.com/soc/net/tw/strong_links.json?screen_name=%s&apikey=%s'


def getRedisIdByUserId(user_id, key_name):
    return 'user_id$' + str(user_id) + '$' + key_name


r = redis.Redis()  # default connection settings on localhost

try:
    response = urllib2.urlopen(API_ENDPOINT % (SCREEN_NAME, API_KEY))
except urllib2.URLError, e:
    print 'Failed to fetch ' + url
    raise e

strong_links = json.loads(response.read())

# resolve screen names and print to screen:

print "%s's Strong Links" % (SCREEN_NAME, )
print '-' * 30
for sl in strong_links['strong_links']:

    try:
        user_info = json.loads(r.get(getRedisIdByUserId(sl[0], 'info.json')))
        print user_info['screen_name'], sl[1]
    except Exception, e:
        print "ERROR: couldn't resolve screen_name for", sl

