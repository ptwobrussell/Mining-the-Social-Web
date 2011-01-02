# -*- coding: utf-8 -*-

import sys
from urllib import urlencode
import json
import urllib2
from facebook__login import login


class FQL(object):

    ENDPOINT = 'https://api.facebook.com/method/'

    def __init__(self, access_token=None):
        self.access_token = access_token

    def _fetch(cls, url, params=None):
        conn = urllib2.urlopen(url, data=urlencode(params))
        try:
            return json.loads(conn.read())
        finally:
            conn.close()

    def query(self, q):
        if q.strip().startswith('{'):
            return self.multiquery(q)
        else:
            params = dict(query=q, access_token=self.access_token, format='json')
            url = self.ENDPOINT + 'fql.query'
            return self._fetch(url, params=params)

    def multiquery(self, q):
        params = dict(queries=q, access_token=self.access_token, format='json')
        url = self.ENDPOINT + 'fql.multiquery'
        return self._fetch(url, params=params)


# Sample usage...

if __name__ == '__main__':
    try:
        ACCESS_TOKEN = open('out/facebook.access_token').read()
        Q = sys.argv[1]
    except IOError, e:
        try:

            # If you pass in the access token from the Facebook app as a command line
            # parameter, be sure to wrap it in single quotes so that the shell
            # doesn't interpret any characters in it. You may also need to escape 
            # the # character

            ACCESS_TOKEN = sys.argv[1]
            Q = sys.argv[2]
        except IndexError, e:
            print >> sys.stderr, \
                "Could not either find access token in 'facebook.access_token' or parse args."
            ACCESS_TOKEN = login()
            Q = sys.argv[1]

    fql = FQL(access_token=ACCESS_TOKEN)
    result = fql.query(Q)
    print json.dumps(result, indent=4)
