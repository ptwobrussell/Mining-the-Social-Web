# -*- coding: utf-8 -*-

import os
import sys
import shutil
import cPickle
import json
import webbrowser
from urllib2 import HTTPError
from geopy import geocoders

# Use your own API key here if you use a geocoding service
# such as Google or Yahoo!

GEOCODING_API_KEY = sys.argv[1]
CONNECTIONS_PICKLE = sys.argv[2]

# An HTML page that we'll inject Protovis consumable data into
HTML_TEMPLATE = '../web_code/protovis/dorling_cartogram/dorling_cartogram.html'
OUT = os.path.basename(HTML_TEMPLATE)

# Open up your saved connections with extended profile information

extended_connections = cPickle.load(open(CONNECTIONS_PICKLE))
locations = [ec.location for ec in extended_connections]

g = geocoders.Yahoo(GEOCODING_API_KEY)

# Some basic transforms may be necessary for geocoding services to function properly

transforms = [('Greater ', ''), (' Area', ''), ('San Francisco Bay',
              'San Francisco')]

# Tally the frequency of each location

freqs = {}
for location in locations:

    # Avoid unnecessary I/O

    if freqs.has_key(location):
        freqs[location][1] += 1
        continue

    transformed_location = location
    for transform in transforms:
        transformed_location = transformed_location.replace(*transform)

    while True:
        num_errors = 0
        try:

            # This call returns a generator

            results = g.geocode(transformed_location, exactly_one=False)
            break
        except HTTPError, e:
            num_errors += 1
            if num_errors >= 3:
                sys.exit()
            print e
            print 'Encountered an urllib2 error. Trying again...'

    for result in results:

        # Each result is of the form ("Description", (X,Y))

        (desc, coords) = result
        state = desc.split(',')[1].strip()
        freqs[location] = [state, 1]
        break

# Roll up frequencies for each state and
# emit output expected by Protovis for Dorling Cartogram

json_data = {}
for (city, [state, freq]) in freqs.items():

    # The results from geocoding probably won't be perfect,
    # and you may have some fixing up to do. For example, Washington DC
    # may resolve to "DC", and you'll need to combine it with VA or MD.
    # Keep in mind that locations that don't resolve to valid 2-letter
    # state codes will be ignored.

    if state == 'DC':
        state = 'VA'

    if not json_data.has_key(state):
        json_data[state] = {'value': 0}
    json_data[state]['value'] += freq

# This json_data is consumed by dorling_cartogram.html
if not os.path.isdir('out'):
    os.mkdir('out')

# HTML_TEMPLATE references some Protovis scripts, which we can
# simply copy into out/

shutil.rmtree('out/dorling_cartogram', ignore_errors=True)
shutil.rmtree('out/protovis-3.2', ignore_errors=True)

shutil.copytree('../web_code/protovis/dorling_cartogram',
                'out/dorling_cartogram')

shutil.copytree('../web_code/protovis/protovis-3.2',
                'out/protovis-3.2')

html = open(HTML_TEMPLATE).read() % (json.dumps(json_data),)
f = open(os.path.join(os.getcwd(), 'out', 'dorling_cartogram', OUT), 'w')
f.write(html)
f.close()

print >> sys.stderr, 'Data file written to: %s' % f.name
webbrowser.open('file://' + f.name)
