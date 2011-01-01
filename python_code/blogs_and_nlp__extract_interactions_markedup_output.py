# -*- coding: utf-8 -*-

import os
import sys
import nltk
import json
from blogs_and_nlp__extract_interactions import extract_interactions

HTML_TEMPLATE = """<html>
    <head>
        <title>%s</title>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
    </head>
    <body>%s</body>
</html>"""

if __name__ == '__main__':

    # Read in output from blogs_and_nlp__get_feed.py

    BLOG_DATA = sys.argv[1]
    blog_data = json.loads(open(BLOG_DATA).read())

    # Marked up version can be written out to disk

    if not os.path.isdir('out/interactions'):
        os.makedirs('out/interactions')

    for post in blog_data:

        post.update(extract_interactions(post['content']))

        # Display output as markup with entities presented in bold text

        post['markup'] = []

        for sentence_idx in range(len(post['sentences'])):

            s = post['sentences'][sentence_idx]
            for (term, _) in post['entity_interactions'][sentence_idx]:
                s = s.replace(term, '<strong>%s</strong>' % (term, ))

            post['markup'] += [s]
        
        filename = post['title'] + '.entity_interactions.html'
        f = open(os.path.join('out', 'interactions', filename), 'w')
        html = HTML_TEMPLATE % (post['title'] + ' Interactions', ' '.join(post['markup']),)
        f.write(html.encode('utf-8'))
        f.close()

        print >> sys.stderr, "Data written to", f.name
