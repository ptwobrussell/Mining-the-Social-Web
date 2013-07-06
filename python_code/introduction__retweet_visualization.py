# -*- coding: utf-8 -*-

import sys
import os
import json
import re
import webbrowser
import codecs
import twitter
import networkx as nx

print >> sys.stderr, """This example has been updated to use Twitter's v1.1 API, which now requires authentication for *all* requests (amongst other things.) 

To run this example, you'll just need to go to http://twitter.com/apps/new to create an app and get authentication credentials that should be inserted into this file's source code. See https://dev.twitter.com/docs/auth/oauth for more information on Twitter's OAuth implementation"""

# Fill in these 4 values
CONSUMER_KEY = ''
CONSUMER_SECRET = ''
OAUTH_TOKEN = ''
OAUTH_TOKEN_SECRET = ''

# Your query - pass it in as a command line parameter (or hard code it if you prefer)
Q = sys.argv[1]

# An HTML page that we'll inject Protovis consumable data into
HTML_TEMPLATE = '../web_code/protovis/twitter_retweet_graph.html'
OUT = os.path.basename(HTML_TEMPLATE)
OUT_DIR = 'out'

# Writes out a DOT language file that can be converted into an 
# image by Graphviz
def write_dot_output(g, out_file):

    out_file += ".dot"

    if not os.path.isdir(OUT_DIR):
        os.mkdir(OUT_DIR)

    try:
        nx.drawing.write_dot(g, os.path.join(OUT_DIR, out_file))
        print >> sys.stderr, 'Data file written to: %s' % os.path.join(os.getcwd(), OUT_DIR, out_file)
    except (ImportError, UnicodeEncodeError):

        # This block serves two purposes:
        # 1) Help for Windows users who will almost certainly not get nx.drawing.write_dot to work 
        # 2) It handles a UnicodeEncodeError that surfaces in write_dot. Appears to be a
        # bug in the source for networkx. Below, codecs.open shows one way to handle it.
        # This except block is not a general purpose method for write_dot, but is representative of
        # the same output write_dot would provide for this graph
        # if installed and easy to implement

        dot = ['"%s" -> "%s" [tweet_id=%s]' % (n1, n2, g[n1][n2]['tweet_id'])
               for (n1, n2) in g.edges()]
        f = codecs.open(os.path.join(os.getcwd(), OUT_DIR, out_file), 'w', encoding='utf-8')
        f.write('''strict digraph {
    %s
    }''' % (';\n'.join(dot), ))
        f.close()

        print >> sys.stderr, 'Data file written to: %s' % f.name

        return f.name

# Writes out an HTML page that can be opened in the browser
# that displays a graph 
def write_protovis_output(g, out_file):
    nodes = g.nodes()
    indexed_nodes = {}

    idx = 0
    for n in nodes:
        indexed_nodes.update([(n, idx,)])
        idx += 1

    links = []
    for n1, n2 in g.edges():
        links.append({'source' : indexed_nodes[n2], 
                      'target' : indexed_nodes[n1]})

    json_data = json.dumps({"nodes" : [{"nodeName" : n} for n in nodes], "links" : links}, indent=4)
    html = open(HTML_TEMPLATE).read() % (json_data,)
    if not os.path.isdir(OUT_DIR):
        os.mkdir(OUT_DIR)
    f = open(os.path.join(os.getcwd(), OUT_DIR, out_file + ".html"), 'w')
    f.write(html)
    f.close()

    print >> sys.stderr, 'Data file written to: %s' % f.name

    return f.name

# Given a tweet, pull out any retweet origins in it and return as a list
def get_rt_origins(tweet):
    # Regex adapted from 
    # http://stackoverflow.com/questions/655903/python-regular-expression-for-retweets
    rt_patterns = re.compile(r"(RT|via)((?:\b\W*@\w+)+)", re.IGNORECASE)
    rt_origins = []

    try:
        rt_origins += [mention.strip() for mention in rt_patterns.findall(tweet)[0][1].split()]
    except IndexError, e:
        pass

    return [rto.strip("@") for rto in rt_origins]


# Authenticate and then get some search results for a query
auth = twitter.oauth.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET,
                           CONSUMER_KEY, CONSUMER_SECRET)

twitter_api = twitter.Twitter(domain='api.twitter.com', 
                              api_version='1.1',
                              auth=auth
                             )

search_results = twitter_api.search.tweets(q=Q, count=100)
tweets = search_results['statuses']

for _ in range(5): # Get 5 more pages
    try:
        next_results = search_results['search_metadata']['next_results']
    except KeyError, e: # No more results when next_results doesn't exist
        break

    # Create a dictionary from the query string params
    kwargs = dict([ kv.split('=') for kv in next_results[1:].split("&") ]) 

    search_results = twitter_api.search.tweets(**kwargs)
    tweets += search_results['statuses']

# Build up a graph data structure
g = nx.DiGraph()

for tweet in tweets:
    rt_origins = get_rt_origins(tweet['text'])
    if not rt_origins:
        continue
    for rt_origin in rt_origins:
        g.add_edge(rt_origin, tweet['user']['screen_name'], {'tweet_id': tweet['id']})

# Print out some stats
print >> sys.stderr, "Number nodes:", g.number_of_nodes()
print >> sys.stderr, "Num edges:", g.number_of_edges()
print >> sys.stderr, "Num connected components:", len(nx.connected_components(g.to_undirected()))
print >> sys.stderr, "Node degrees:", sorted(nx.degree(g))

# Write Graphviz output
write_dot_output(g, OUT)

# Write Protovis output and open in browser
protovis_output = write_protovis_output(g, OUT)
webbrowser.open('file://' + protovis_output)
