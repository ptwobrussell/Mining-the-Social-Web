# -*- coding: utf-8 -*-

import sys
import json
import nltk
import numpy

# Load in human readable text from wherever you've saved it

BLOG_DATA = sys.argv[1]
blog_data = json.loads(open(BLOG_DATA).read())

N = 100  # Number of words to consider
CLUSTER_THRESHOLD = 5  # Distance between words to consider
TOP_SENTENCES = 5  # Number of sentences to return for a "top n" summary

# Approach taken from "The Automatic Creation of Literature Abstracts" by H.P. Luhn


def score_sentences(sentences, important_words):
    scores = []
    sentence_idx = -1

    for s in [nltk.tokenize.word_tokenize(s) for s in sentences]:

        sentence_idx += 1
        word_idx = []

        # For each word in the word list...

        for w in important_words:
            try:

                # Compute an index for where any important words occur in the sentence

                word_idx.append(s.index(w))
            except ValueError, e:
                pass

        word_idx.sort()

        # Using the word index, compute clusters by using a max distance threshold
        # for any two consecutive words

        clusters = []
        cluster = [word_idx[0]]
        i = 1
        while i < len(word_idx):
            if word_idx[i] - word_idx[i - 1] < CLUSTER_THRESHOLD:
                cluster.append(word_idx[i])
            else:
                clusters.append(cluster[:])
                cluster = [word_idx[i]]
            i += 1
        clusters.append(cluster)

        # Score each cluster. The max score for any given cluster is the score for the sentence

        max_cluster_score = 0
        for c in clusters:
            significant_words_in_cluster = len(c)
            total_words_in_cluster = c[-1] - c[0] + 1
            score = 1.0 * significant_words_in_cluster \
                * significant_words_in_cluster / total_words_in_cluster

            if score > max_cluster_score:
                max_cluster_score = score

        scores.append((sentence_idx, score))

    return scores


for post in blog_data:
    sentences = [s for s in nltk.tokenize.sent_tokenize(post['content'])]
    normalized_sentences = [s.lower() for s in sentences]

    words = [w.lower() for sentence in normalized_sentences for w in
             nltk.tokenize.word_tokenize(sentence)]

    fdist = nltk.FreqDist(words)

    top_n_words = [w[0] for w in fdist.items() if w[0]
                   not in nltk.corpus.stopwords.words('english')][:N]

    scored_sentences = score_sentences(normalized_sentences, top_n_words)

    # Summaization Approach 1:
    # Filter out non-significant sentences by using the average score plus a
    # fraction of the std dev as a filter

    avg = numpy.mean([s[1] for s in scored_sentences])
    std = numpy.std([s[1] for s in scored_sentences])
    mean_scored = [(sent_idx, score) for (sent_idx, score) in scored_sentences
                   if score > avg + 0.5 * std]

    # Summarization Approach 2:
    # Another approach would be to return only the top N ranked sentences

    top_n_scored = sorted(scored_sentences, key=lambda s: s[1])[-TOP_SENTENCES:]
    top_n_scored = sorted(top_n_scored, key=lambda s: s[0])

    # Decorate the post object with summaries

    post['top_n_summary'] = [sentences[idx] for (idx, score) in top_n_scored]
    post['mean_scored_summary'] = [sentences[idx] for (idx, score) in mean_scored]

    # Optionally save back out the data...

    print post['title']
    print '-' * len(post['title'])
    print
    print 'Top N Summary'
    print '---------'
    print post['top_n_summary']
    print
    print 'Mean Scored Summary'
    print '---------'
    print post['mean_scored_summary']
    print
