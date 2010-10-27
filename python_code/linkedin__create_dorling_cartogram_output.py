# -*- coding: utf-8 -*-

import sys
import cPickle
import json
from urllib2 import HTTPError
from geopy import geocoders

# Use your own API key here if you use a geocoding service
# such as Google or Yahoo!

GEOCODING_API_KEY = sys.argv[1]
CONNECTIONS_PICKLE = sys.argv[2]

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

output = {}
for (city, [state, freq]) in freqs.items():

    # The results from geocoding probably won't be perfect,
    # and you may have some fixing up to do. For example, Washington DC
    # may resolve to "DC", and you'll need to combine it with VA or MD.
    # Keep in mind that locations that don't resolve to valid 2-letter
    # state codes will be ignored.

    if state == 'DC':
        state = 'VA'

    if not output.has_key(state):
        output[state] = {'value': 0}
    output[state]['value'] += freq

# This output is consumed by dorling_cartogram.html

f = open('dorling_cartogram.js', 'w')
f.write('var _data = %s;' % (json.dumps(output, indent=4), ))
f.close()
