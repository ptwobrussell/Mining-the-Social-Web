# -*- coding: utf-8 -*-

import sys
import webbrowser
import cPickle
from linkedin import linkedin

KEY = sys.argv[1]
SECRET = sys.argv[2]

# Parses out oauth_verifier parameter from window.location.href and
# displays it for the user

RETURN_URL = 'http://miningthesocialweb.appspot.com/static/linkedin_oauth_helper.html'


def oauthDance(key, secret, return_url):
    api = linkedin.LinkedIn(key, secret, return_url)

    result = api.requestToken()

    if not result:
        print api.requestTokenError()
        return None

    authorize_url = api.getAuthorizeURL()

    webbrowser.open(authorize_url)

    oauth_verifier = raw_input('PIN number, bro: ')

    result = api.accessToken(verifier=oauth_verifier)
    if not result:
        print 'Error: %s\nAborting' % api.getRequestTokenError()
        return None

    return api


# First, do the oauth_dance

api = oauthDance(KEY, SECRET, RETURN_URL)

# Now do something like get your connections:

if api:
    connections = api.GetConnections()
else:
    print 'Failed to aunthenticate. You need to learn to dance'
    sys.exit(1)

# Be careful - this type of API usage limits you to 500 calls per day

extended_connections = [api.GetProfile(member_id=c.id, url=None, fields=[
    'first-name',
    'last-name',
    'current-status',
    'educations',
    'specialties',
    'interests',
    'honors',
    'positions',
    'industry',
    'summary',
    'location',
    ]) for c in connections]

# Store these out wherever it's handy

f = open('linkedin_connections.pickle', 'wb')
cPickle.dump(extended_connections, f)
f.close()
