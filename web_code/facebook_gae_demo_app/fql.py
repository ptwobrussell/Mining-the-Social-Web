# -*- coding: utf-8 -*-

from urllib import urlencode
try:
    from django.utils import simplejson as json
except:
    import json

try:
    from google.appengine.api import urlfetch
except:
    import urllib2

class FQL(object):
    
    ENDPOINT = 'https://api.facebook.com/method/'
    
    def __init__(self, access_token=None):
        self.access_token = access_token
    
    def __call__(self, query, **params):
        
        params.update(query=query, access_token=self.access_token, format='json')
        url = self.ENDPOINT + 'fql.query'
        return self.fetch_json(url, data=urlencode(params))
    
    def multi(self, queries, **params):
        params.update(queries=json.dumps(queries), access_token=self.access_token, format='json')
        url = self.ENDPOINT + 'fql.multiquery'
        return self.fetch_json(url, data=urlencode(params))
    
    def fetch_json(cls, url, data=None):
        result = urlfetch.fetch(url, deadline=30, method=urlfetch.POST, payload=data)
        return json.loads(result.content)

    def local_call(self, query, **params):
        params.update(query=query, access_token=self.access_token, format='json')
        url = self.ENDPOINT + 'fql.query'
        conn = urllib2.urlopen(url, data=urlencode(params))
        try:
            return conn.read()
        finally:
            conn.close()

