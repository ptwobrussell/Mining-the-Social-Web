# -*- coding: utf-8 -*-

import os
import sys
import json
import facebook
import webbrowser
from facebook__fql_query import FQL
from facebook__login import login

HTML_TEMPLATE = '../web_code/dojo/facebook.current_locations_and_hometowns.html'

try:
    ACCESS_TOKEN = open('out/facebook.access_token').read()
except IOError, e:
    try:

        # If you pass in the access token from the Facebook app as a command line
        # parameter, be sure to wrap it in single quotes so that the shell
        # doesn't interpret any characters in it. You may also need to escape 
        # the # character

        ACCESS_TOKEN = sys.argv[1]
    except IndexError, e:
        print >> sys.stderr, \
            "Could not either find access token in 'facebook.access_token' or parse args."
        ACCESS_TOKEN = login()

# process the results of the following fql query to create a json output suitable for
# consumption by a simple hierarchical tree widget:

fql = FQL(ACCESS_TOKEN)

q = \
"""select name, current_location, hometown_location from user where uid in
  (select target_id from connection where source_id = me() and target_type = 'user')"""
results = fql.query(q)

# First, read over the raw fql query and create a hierarchical maps that groups people by 
# where they live now compared to their hometown. we'll simply tabulate frequencies, but 
# you could easily grab additional data in the fql and use it for many creative situations

current_by_hometown = {}
for r in results:
    if r['current_location'] != None:
        current_location = r['current_location']['city'] + ', ' \
            + r['current_location']['state']
    else:
        current_location = 'Unknown'

    if r['hometown_location'] != None:
        hometown_location = r['hometown_location']['city'] + ', ' \
            + r['hometown_location']['state']
    else:
        hometown_location = 'Unknown'

    if current_by_hometown.has_key(hometown_location):
        if current_by_hometown[hometown_location].has_key(current_location):
            current_by_hometown[hometown_location][current_location] += [r['name'
                    ]]
        else:
            current_by_hometown[hometown_location][current_location] = [r['name']]
    else:
        current_by_hometown[hometown_location] = {}
        current_by_hometown[hometown_location][current_location] = [r['name']]

# from here, there are a lot different ways you could slice and dice the data now that 
# it's in a reasonable data structure.
# let's create a hierarchical structure that lends itself to being displayed as a tree.

items = []
for hometown in current_by_hometown:
    num_from_hometown = sum([len(current_by_hometown[hometown][current])
                            for current in current_by_hometown[hometown]])
    name = '%s (%s)' % (hometown, num_from_hometown)
    try:
        hometown_state = hometown.split(',')[1]
    except IndexError:
        hometown_state = hometown
    item = {'name': name, 'state': hometown_state,
            'num_from_hometown': num_from_hometown}

    item['children'] = []
    for current in current_by_hometown[hometown]:
        try:
            current_state = current.split(',')[1]
        except IndexError:
            current_state = current

        item['children'].append({'name': '%s (%s)' % (current,
                                len(current_by_hometown[hometown][current])),
                                'state': current_state, 'children': [{'name'
                                : f[:f.find(' ') + 2] + '.'} for f in
                                current_by_hometown[hometown][current]]})

    # sort items alphabetically by state. further roll up by state could 
    # be done here if desired

    item['children'] = sorted(item['children'], key=lambda i: i['state'])
    items.append(item)

# optionally, roll up outer level items by state to create a better user experience in 
# the display. alternatively, you could just pass the current value of items in the final 
# statement that creates the json output for smaller data sets

items = sorted(items, key=lambda i: i['state'])
all_items_by_state = []
grouped_items = []
current_state = items[0]['state']
num_from_state = items[0]['num_from_hometown']
for item in items:
    if item['state'] == current_state:
        num_from_state += item['num_from_hometown']
        grouped_items.append(item)
    else:
        all_items_by_state.append({'name': '%s (%s)' % (current_state,
                                  num_from_state), 'children': grouped_items})
        current_state = item['state']
        num_from_state = item['num_from_hometown']
        grouped_items = [item]
all_items_by_state.append({'name': '%s (%s)' % (current_state, num_from_state),
                          'children': grouped_items})

# finally, emit output suitable for consumption by a hierarchical tree widget

if not os.path.isdir('out'):
    os.mkdir('out')

f = open(os.path.join('out', 'facebook.current_locations_and_hometowns.json'), 'w'
         )
f.write(json.dumps({'items': all_items_by_state, 'label': 'name'}, indent=4))
f.close()

print >> sys.stderr, 'Data file written to: %s' % f.name

# Write out  a web page

html = open(HTML_TEMPLATE).read() % (json.dumps({'items': all_items_by_state,
                                     'label': 'name'}, indent=4), )
f = open(os.path.join('out', 'facebook.current_locations_and_hometowns.html'), 'w'
         )
f.write(html)
f.close()

# Open up the web page in your browser

webbrowser.open('file://' + os.path.join(os.getcwd(), 'out',
                'facebook.current_locations_and_hometowns.html'))
