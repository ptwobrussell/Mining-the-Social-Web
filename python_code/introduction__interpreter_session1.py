# -*- coding: utf-8 -*-

import os
import cPickle
import re
import networkx as nx

OUT = 'snl_search_results.dot'

search_results = \
    cPickle.load(open(os.path.join(*'../dot_dot_slash/data/ch01-snl_search_results.pickle'.split('/'
                 ))))
g = nx.DiGraph()

all_tweets = [tweet for page in search_results for tweet in page['results']]


def get_rt_sources(tweet):
    rt_patterns = re.compile(r"(RT|via)((?:\b\W*@\w+)+)", re.IGNORECASE)
    return [source.strip() for tuple in rt_patterns.findall(tweet) for source in
            tuple if source not in ('RT', 'via')]


for tweet in all_tweets:
    rt_sources = get_rt_sources(tweet['text'])
    if not rt_sources:
        continue
    for rt_source in rt_sources:
        g.add_edge(rt_source, tweet['from_user'], {'tweet_id': tweet['id']})

print g.number_of_nodes()
print g.number_of_edges()
print len(nx.connected_components(g.to_undirected()))
print sorted(nx.degree(g))

try:
    nx.drawing.write_dot(g, OUT)
except ImportError, e:

    # Help for Windows users:
    # Not a general purpose method, but representative of
    # the same output write_dot would provide for this graph
    # if installed and easy to implement

    dot = ['"%s" -> "%s" [tweet_id=%s]' % (n1, n2, g[n1][n2]['tweet_id'])
           for (n1, n2) in g.edges()]
    f = open(OUT, 'w')
    f.write('''strict digraph {
%s
}''' % (';\n'.join(dot), ))
    f.close()
