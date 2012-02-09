# -*- coding: utf-8 -*-

# Instructions for using this script:
#
# 0. Install dependencies: 
#    $ easy_install --upgrade google-api-python-client
# 1. Go to: https://code.google.com/apis/console
# 2. Under 'Services', enable Google Plus API Access
# 3. Under 'API Access', use the 'API key' value to populate 
#    the API_KEY variable below
# 4. Execute this script as $ python plus_get_activities <user id>

import os
import sys
import httplib2
import json
import apiclient.discovery
from BeautifulSoup import BeautifulStoneSoup
from nltk import clean_html

USER_ID=sys.argv[1] # Tim O'Reilly's Google+ id is '107033731246200681024'

API_KEY=None # Supply your own API key value.

MAX_RESULTS = 200 # May actually get slightly more 

# Helper function for removing html and converting escaped entities. 
# Returns UTF-8

def cleanHtml(html):
  if html == "": return ""

  return BeautifulStoneSoup(clean_html(html),
          convertEntities=BeautifulStoneSoup.HTML_ENTITIES).contents[0]

service = apiclient.discovery.build('plus', 'v1', http=httplib2.Http(), 
                                    developerKey=API_KEY)

activities_resource = service.activities()
request = activities_resource.list(
  userId=USER_ID,
  collection='public',
  maxResults='100') # Max allowed per API

activities = []

while request != None and len(activities) < MAX_RESULTS:

  activities_document = request.execute()

  if 'items' in activities_document:

    for activity in activities_document['items']:

      if activity['object']['objectType'] == 'note' and \
         activity['object']['content'] != '':

        activity['title'] = cleanHtml(activity['title'])
        activity['object']['content'] = cleanHtml(activity['object']['content'])
        activities.append(activity)

  request = service.activities().list_next(request, activities_document)

# Store out to a local file as json data if you prefer

if not os.path.isdir('out'):
    os.mkdir('out')

filename = os.path.join('out', USER_ID + '.plus')
f = open(filename, 'w')
f.write(json.dumps(activities, indent=2))
f.close()

print >> sys.stderr, str(len(activities)), "activities written to", f.name

# Or store it somewhere like CouchDB like so...

# server = couchdb.Server('http://localhost:5984')
# DB = 'plus-' + USER_ID
# db = server.create(DB)
# db.update(activities, all_or_nothing=True)
