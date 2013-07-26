# -*- coding: utf-8 -*-

import os
import sys
import cPickle
from linkedin import linkedin
from linkedin.exceptions import LinkedInError

CONSUMER_KEY = sys.argv[1]
CONSUMER_SECRET = sys.argv[2]
USER_TOKEN = sys.argv[3]
USER_SECRET = sys.argv[4]

# Parses out oauth_verifier parameter from window.location.href and
# displays it for the user

RETURN_URL = 'http://miningthesocialweb.appspot.com/static/linkedin_oauth_helper.html'

authentication = linkedin.LinkedInDeveloperAuthentication(CONSUMER_KEY, CONSUMER_SECRET,
                                                          USER_TOKEN, USER_SECRET,
                                                          RETURN_URL, linkedin.PERMISSIONS.enums.values())
# Pass it in to the app...

api = linkedin.LinkedInApplication(authentication)

# Now do something like get your connections:

if api:
    connections = api.get_connections()
else:
    print >> sys.stderr, 'Failed to authenticate. You need to learn to dance'
    sys.exit(1)

# Be careful - this type of API usage is "expensive".
# See http://developer.linkedin.com/docs/DOC-1112

print >> sys.stderr, 'Fetching extended connections...'

extended_connections = []
try:
    for c in connections['values']:
        extended_connections.append(api.get_profile(member_id=c['id'], member_url=None, selectors=[
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
        ]))
except LinkedInError:
    pass

# Store the data

if not os.path.isdir('out'):
    os.mkdir('out')

f = open('out/linkedin_connections.pickle', 'wb')
cPickle.dump(extended_connections, f)
f.close()

print >> sys.stderr, 'Data pickled to out/linkedin_connections.pickle'
