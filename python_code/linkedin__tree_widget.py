import os
import sys
import json
import webbrowser
from linkedin__cluster_contacts_by_title import cluster_contacts_by_title

CSV_FILE = sys.argv[1]

HTML_TEMPLATE = '../web_code/dojo/dojo_tree.html'

data = {"label" : "name", "temp_items" : {}, "items" : []}

clustered_contacts = cluster_contacts_by_title(CSV_FILE)

for titles in clustered_contacts:
    descriptive_terms = set(titles[0].split())
    for title in titles:
        descriptive_terms.intersection_update(set(title.split()))
    descriptive_terms = ', '.join(descriptive_terms)

    if data['temp_items'].has_key(descriptive_terms):
        data['temp_items'][descriptive_terms].extend([{'name' : cc } for cc
            in clustered_contacts[titles]])
    else:
        data['temp_items'][descriptive_terms] = [{'name' : cc } for cc
            in clustered_contacts[titles]]

for descriptive_terms in data['temp_items']:
    data['items'].append({"name" : "%s (%s)" % (descriptive_terms,
        len(data['temp_items'][descriptive_terms]),),
            "children" : [i for i in
                data['temp_items'][descriptive_terms]]})

del data['temp_items']

# Open the template and substitute the data

if not os.path.isdir('out'):
    os.mkdir('out')

OUT = os.path.join('out', 'dojo_tree.html')

t = open(HTML_TEMPLATE).read()
f = open(OUT, 'w')
f.write(t % json.dumps(data, indent=4))
f.close()

webbrowser.open("file://" + os.path.join(os.getcwd(), OUT))
