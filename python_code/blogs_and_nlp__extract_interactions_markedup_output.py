# -*- coding: utf-8 -*-

import sys
import nltk
import json

# Load in human readable text from wherever you've saved it

BLOG_DATA = sys.argv[1]
blog_data = json.loads(open(BLOG_DATA).read())

for post in blog_data:

    sentences = nltk.tokenize.sent_tokenize(post['content'])
    tokens = [nltk.tokenize.word_tokenize(s) for s in sentences]
    pos_tagged_tokens = [nltk.pos_tag(t) for t in tokens]

    post['entity_interactions'] = []
    for sentence in pos_tagged_tokens:

        all_entity_chunks = []
        previous_pos = None
        current_entity_chunk = []

        for (token, pos) in sentence:

            if pos == previous_pos and pos.startswith('NN'):
                current_entity_chunk.append(token)
            elif pos.startswith('NN'):
                if current_entity_chunk != []:
                    all_entity_chunks.append((' '.join(current_entity_chunk),
                            pos))
                current_entity_chunk = [token]

            previous_pos = pos

        if len(all_entity_chunks) > 1:
            post['entity_interactions'].append(all_entity_chunks)
        else:
            post['entity_interactions'].append([])

    # Display output as markup with entities presented in bold text

    post['markup'] = []

    for sentence_idx in range(len(sentences)):

        s = sentences[sentence_idx]
        for (term, _) in post['entity_interactions'][sentence_idx]:
            s = s.replace(term, '<strong>%s</strong>' % (term, ))

        post['markup'] += [s]

    f = open(post['title'] + '.entity_interactions.html', 'w')
    f.write('<p>%s</p>' % (' '.join(post['markup']), ))
    f.close()
