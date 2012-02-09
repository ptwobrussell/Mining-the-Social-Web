# -*- coding: utf-8 -*-

import os
import sys
import shutil
import webbrowser
from random import shuffle
import json
from operator import itemgetter
import nltk
import numpy

# Load in textual data from wherever you've saved it

DATA = sys.argv[1]
data = json.loads(open(DATA).read())

# Take a random sample so that a meaningful visualization can be displayed

shuffle(data)
data = data[:25]

# HTML templmates that we'll inject Protovis consumable data into

HTML_TEMPLATES = ['../web_code/protovis/matrix_diagram.html', 
                  '../web_code/protovis/arc_diagram.html']

activities = [activity['object']['content'].lower().split() for activity in data]

# Provides tf/idf/tf_idf abstractions for scoring

tc = nltk.TextCollection(activities)

# Compute a term-document matrix such that td_matrix[doc_title][term]
# returns a tf-idf score for the term in the document

td_matrix = {}
for idx in range(len(activities)):
    activity = activities[idx]
    fdist = nltk.FreqDist(activity)

    doc_title = data[idx]['title']
    url = data[idx]['url']
    td_matrix[(doc_title, url)] = {}

    for term in fdist.iterkeys():
        td_matrix[(doc_title, url)][term] = tc.tf_idf(term, activity)

# Build vectors such that term scores are in the same positions...

distances = {}
for (title1, url1) in td_matrix.keys():

    distances[(title1, url1)] = {}

    for (title2, url2) in td_matrix.keys():

        if url1 == url2:
            continue

        # Take care not to mutate the original data structures
        # since we're in a loop and need the originals multiple times

        terms1 = td_matrix[(title1, url1)].copy()
        terms2 = td_matrix[(title2, url2)].copy()

        # Fill in "gaps" in each map so vectors of the same length can be computed

        for term1 in terms1:
            if term1 not in terms2:
                terms2[term1] = 0

        for term2 in terms2:
            if term2 not in terms1:
                terms1[term2] = 0

        # Create vectors from term maps

        v1 = [score for (term, score) in sorted(terms1.items())]
        v2 = [score for (term, score) in sorted(terms2.items())]

        # Compute similarity amongst documents

        distances[(title1, url1)][(title2, url2)] = \
            nltk.cluster.util.cosine_distance(v1, v2)

# Compute the standard deviation for the distances as a basis of automated thresholding

std = numpy.std([distances[k1][k2] for k1 in distances for k2 in distances[k1]])

similar = []
keys = td_matrix.keys()

for k1 in keys:
    for k2 in keys:
        if k1 == k2:
            continue

        d = distances[k1][k2]
        if d < std / 2 and d > 0.000001:  # call them similar
            (title1, url1) = k1
            (title2, url2) = k2
            similar.append((k1, k2, distances[k1][k2]))

# Emit output expected by Protovis.

nodes = {}
node_idx = 0
edges = []
for s in similar:
    if s[0] not in nodes:
        nodes[s[0]] = node_idx
        node_idx += 1

    node0 = nodes[s[0]]

    if s[1] not in nodes:
        nodes[s[1]] = node_idx
        node_idx += 1

    node1 = nodes[s[1]]

    edges.append({'source': node0, 'target': node1, 'value': s[2] * 100})

nodes = [{'nodeName': title, 'nodeUrl': url} for ((title, url), idx) in
         sorted(nodes.items(), key=itemgetter(1))]

json_data = {'nodes': nodes, 'links': edges}

# This json_data is consumed by matrix_diagram.html
if not os.path.isdir('out'):
    os.mkdir('out')

# HTML_TEMPLATE references some Protovis scripts, which we can
# simply copy into out/

shutil.rmtree('out/protovis-3.2', ignore_errors=True)

shutil.copytree('../web_code/protovis/protovis-3.2',
                'out/protovis-3.2')


for template in HTML_TEMPLATES:
    html = open(template).read() % (json.dumps(json_data),)
    f = open(os.path.join(os.getcwd(), 'out', os.path.basename(template)), 'w')
    f.write(html)
    f.close()

    print >> sys.stderr, 'Data file written to: %s' % f.name
    webbrowser.open('file://' + f.name)
