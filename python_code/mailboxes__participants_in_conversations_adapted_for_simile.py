# -*- coding: utf-8 -*-

"""
XXX: This script could be refactored to maximally borrow from
     mailboxes__participants_in_conversations.py
"""

import sys
import os
import httplib
from urllib import quote
from urllib import urlencode
import json
import webbrowser
from dateutil.parser import parse

DB = sys.argv[1]  # enron
QUERY = sys.argv[2]

HTML_TEMPLATE = '../web_code/simile/timeline.html'

# Query couchdb-lucene by_subject and by_content

message_ids_of_interest = []
for idx in ['by_subject', 'by_content']:

    try:
        conn = httplib.HTTPConnection('localhost', 5984)
        conn.request('GET', '/%s/_fti/_design/lucene/%s?q=%s&limit=50000' % (DB,
                     idx, quote(QUERY)))
        response = conn.getresponse()
        if response.status == 200:
            response_body = json.loads(response.read())
            message_ids_of_interest.extend([row['id'] for row in
                    response_body['rows']])
        else:
            print 'An error occurred fetching the response: %s %s' \
                % (response.status, response.reason)
            sys.exit()
    finally:
        conn.close()

# Remove any duplicates

message_ids_of_interest = list(set(message_ids_of_interest))

# Perform discussion thread filtering in memory. It's a relatively
# small amount of data

try:
    conn = httplib.HTTPConnection('localhost', 5984)
    conn.request('GET', '/%s/_all_docs?include_docs=true' % (DB + '-threads', ))
    response = conn.getresponse()
    if response.status != 200:  #  OK
        print 'Unable to get docs: %s %s' % (response.status, response.reason)
        sys.exit()

    threads = [dict([('thread_id', row['doc']['_id']), ('message_ids',
               [t['external_id'] for t in row['doc']['thread']])]) for row in
               json.loads(response.read())['rows']]
finally:
    conn.close()

# Find only the threads that have a message_id appearing in the list of message ids 
# fetched from the Lucene index

threads_of_interest = [t for t in threads for message_id in t['message_ids']
                       if message_id in message_ids_of_interest]

# Remove duplicates

seen = []
idx = 0
while idx < len(threads_of_interest):
    if threads_of_interest[idx]['thread_id'] in seen:
        threads_of_interest.pop(idx)
    else:
        seen.append(threads_of_interest[idx]['thread_id'])
        idx += 1

# Cull out message ids for threads of interest

message_ids_for_threads_of_interest = [t['message_ids'] for t in
                                       threads_of_interest]

# Flatten out the list of lists into just a list and remove duplicates

message_ids_for_threads_of_interest = list(set([message_id for message_ids in
        message_ids_for_threads_of_interest for message_id in message_ids]))

# Query CouchDB for the email addresses in various headers of interest using a bulk request

try:
    conn = httplib.HTTPConnection('localhost', 5984)
    post_params = json.dumps({'keys': message_ids_for_threads_of_interest})
    conn.request('POST', '/%s/_all_docs?include_docs=true' % (DB, ), post_params)
    response = conn.getresponse()
    if response.status != 200:  #  OK
        print 'Unable to get docs: %s %s' % (response.status, response.reason)
        sys.exit()

    full_docs = [row['doc'] for row in json.loads(response.read())['rows']]
finally:
    conn.close()

# Finally, with full messages of interest on hand, parse out headers of interest and
# and compute output for SIMILE Timeline

events = []
for thread in threads_of_interest:

    # Process each thread: create an event object for the thread as well as
    # for individual messages involved in the thread

    participants = []
    message_dates = []
    for message_id in thread['message_ids']:
        doc = [d for d in full_docs if d['_id'] == message_id][0]
        message_dates.append(parse(doc['Date']).isoformat())
        try:
            participants.append(doc.get('From'))
            participants.extend(doc.get('To'))
            if doc.get('Cc'):
                participants.extend(doc.get('Cc'))
            if doc.get('Bcc'):
                participants.extend(doc.get('Bcc'))
        except:
            pass  # Maybe a X-To or X-Origin header, etc. as opposed to To?

        # Append each individual message in the thread

        event = {}
        event['title'] = doc['Subject']
        event['start'] = parse(doc['Date']).isoformat()
        event['durationEvent'] = False
        event['description'] = 'Message involving ' \
            + ', '.join(list(set(participants)))
        event['link'] = 'http://localhost:5984/_utils/document.html?%s/%s' % (DB,
                doc['_id'])
        events.append(event)

    # Find start and end dates for the messages involved in the thread

    if len(thread['message_ids']) > 1:
        event = {}
        event['title'] = doc['Subject']
        message_dates.sort()
        event['start'] = parse(message_dates[0]).isoformat()
        event['end'] = parse(message_dates[-1]).isoformat()
        event['durationEvent'] = True
        event['description'] = str(len(thread['message_ids'])) \
            + ' messages in thread'
        events.append(event)  # append the thread event

if not os.path.isdir('out'):
    os.mkdir('out')

json_output = json.dumps({'dateTimeFormat': 'iso8601', 'events': events}, indent=4)
f = open(os.path.join('out', 'simile_data.json'), 'w')
f.write(json_output)
f.close()

print >> sys.stderr, 'Data file written to: %s' % f.name

# Write out  a web page

html = open(HTML_TEMPLATE).read().replace("%s", json_output) # simple hack
f = open(os.path.join('out', os.path.basename(HTML_TEMPLATE)), 'w')
f.write(html)
f.close()

# Open up the web page in your browser

webbrowser.open('file://' + os.path.join(os.getcwd(), 'out',
                os.path.basename(HTML_TEMPLATE)))
