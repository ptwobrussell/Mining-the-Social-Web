# -*- coding: utf-8 -*-

import os
import sys
import json
import webbrowser
from copy import deepcopy

# Reuses out/facebook.friends.json written out by 
# facebook__get_friends_rgraph.py
DATA = sys.argv[1]
data = json.loads(open(DATA).read())

# Define colors to be used in the visualization
# for aesthetics

colors = ['#FF0000', '#00FF00', '#0000FF']

# The primary output to collect input

out = {
    'id': 'friends',
    'name': 'friends',
    'data': {'$type': 'none'},
    'children': [],
    }

# A convenience template

template = {
    'id': 'friends',
    'name': 'friends',
    'data': {'connections': '', '$angularWidth': 1, '$color': ''},
    'children': [],
    }

i = 0
for g in ['male', 'female']:

    # Create a gender object

    go = deepcopy(template)
    go['id'] += '/' + g
    go['name'] += '/' + g
    go['data']['$color'] = colors[i]

    # Find friends by each gender

    friends_by_gender = [f for f in data if f['data']['sex'] == g]
    for f in friends_by_gender:

        # Load friends into the gender object

        fo = deepcopy(template)
        fo['id'] = f['id']
        fo['name'] = f['name']
        fo['data']['$color'] = colors[i % 3]
        fo['data']['$angularWidth'] = len(f['adjacencies'])  # Rank by global popularity
        fo['data']['connections'] = f['data']['connections']  # For the tooltip

        go['children'].append(fo)

    out['children'].append(go)
    i += 1

# Emit the output expected by the JIT Sunburst

if not os.path.isdir('out'):
    os.mkdir('out')

f = open(os.path.join('out', 'facebook.sunburst.js'), 'w')
f.write('var json = %s;' % (json.dumps(out, indent=4), ))
f.close()

print 'Data file written to: %s' % f.name

# Open up the web page in your browser

webbrowser.open('file://' + os.path.join(os.getcwd(), '..', 'web_code', 'jit',
                'sunburst', 'sunburst.html'))
