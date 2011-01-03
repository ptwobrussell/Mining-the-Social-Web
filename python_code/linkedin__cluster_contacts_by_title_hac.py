# -*- coding: utf-8 -*-

import os
import sys
import csv
import json
import shutil
import webbrowser
from nltk.metrics.distance import masi_distance
from cluster import HierarchicalClustering

HTML_TEMPLATE = '../web_code/protovis/linkedin_tree.html'

# Another option for a template
HTML_TEMPLATE = '../web_code/protovis/linkedin_dendogram.html'

OUT = os.path.basename(HTML_TEMPLATE)


CSV_FILE = sys.argv[1]
DISTANCE_THRESHOLD = 0.34

DISTANCE = masi_distance

transforms = [
    ('Sr.', 'Senior'),
    ('Sr', 'Senior'),
    ('Jr.', 'Junior'),
    ('Jr', 'Junior'),
    ('CEO', 'Chief Executive Officer'),
    ('COO', 'Chief Operating Officer'),
    ('CTO', 'Chief Technology Officer'),
    ('CFO', 'Chief Finance Officer'),
    ('VP', 'Vice President'),
    ]

seperators = ['/', 'and', '&']

csvReader = csv.DictReader(open(CSV_FILE), delimiter=',', quotechar='"')
contacts = [row for row in csvReader]

# Normalize and/or replace known abbreviations
# and build up list of common titles

all_titles = []
for i in range(len(contacts)):
    if contacts[i]['Job Title'] == '':
        contacts[i]['Job Titles'] = ['']
        continue
    titles = [contacts[i]['Job Title']]
    for title in titles:
        for seperator in seperators:
            if title.find(seperator) >= 0:
                titles.remove(title)
                titles.extend([title.strip() for title in title.split(seperator)
                              if title.strip() != ''])

    for transform in transforms:
        titles = [title.replace(*transform) for title in titles]
    contacts[i]['Job Titles'] = titles
    all_titles.extend(titles)

all_titles = list(set(all_titles))

######## Begin: HAC ########

# Define a scoring function


def score(title1, title2):
    return DISTANCE(set(title1.split()), set(title2.split()))


# Feed the class your data and the scoring function

hc = HierarchicalClustering(all_titles, score)

# Cluster the data according to a distance threshold

clusters = hc.getlevel(DISTANCE_THRESHOLD)

# Remove singleton clusters
# clusters = [c for c in clusters if len(c) > 1]

######## End: HAC ########

# Round up contacts who are in these clusters and group them together

clustered_contacts = {}
for cluster in clusters:
    clustered_contacts[tuple(cluster)] = []
    for contact in contacts:
        for title in contact['Job Titles']:
            if title in cluster:
                clustered_contacts[tuple(cluster)].append('%s %s.'
                        % (contact['First Name'], contact['Last Name'][0]))

json_output = {}
for titles in clustered_contacts:

    descriptive_terms = set(titles[0].split())
    for title in titles:
        descriptive_terms.intersection_update(set(title.split()))

    json_output[', '.join(descriptive_terms)[:30]] = dict([(c, None) for c in
            clustered_contacts[titles]])

if not os.path.isdir('out'):
    os.mkdir('out')

# HTML_TEMPLATE references some dependencies that we need to
# copy into out/

shutil.rmtree('out/protovis-3.2', ignore_errors=True)

shutil.copytree('../web_code/protovis/protovis-3.2',
                'out/protovis-3.2')

html = open(HTML_TEMPLATE).read() % (json.dumps(json_output),)
f = open(os.path.join(os.getcwd(), 'out', OUT), 'w')
f.write(html)
f.close()

print 'Data file written to: %s' % f.name

# Open up the web page in your browser

webbrowser.open('file://' + f.name)
