# -*- coding: utf-8 -*-

#################################################################################
# NOTE: The opt-in "include_entities" flag can be passed in as a keyword 
# argument to to t.statuses.show to have Twitter's API extract the entities 
# instead of using the getEntities function as described in this example like so:
#
# tweet = t.statuses.show(id=TWEET_ID, include_entities=1)
# 
# This is a case-in-point of Twitter's API constantly evolving to make the lives
# of developers easier. Their API slowly evolved quite a bit over the course of
# 2010 as Mining the Social Web was being written, and will no doubt continue
# to evolve and obsolete additional examples. Still, however, not all Twitter 
# APIs provide an opt-in parameter for extracting tweet entities (as of early
# January 2010 anyway), and it is likely the case that you'll need to perform 
# this work manually for histroical or archived data that was collected prior 
# to mid- to late-2010 unless 3rd party data providers perform the work for you.
#################################################################################

import sys
import json
import twitter_text
import twitter
from twitter__login import login

# Get a tweet id clicking on a status right off of twitter.com. 
# For example, http://twitter.com/#!/timoreilly/status/17386521699024896

TWEET_ID = sys.argv[1]

def getEntities(tweet):

    # Now extract various entities from it and build up a familiar structure

    extractor = twitter_text.Extractor(tweet['text'])

    # Note that the production Twitter API contains a few additional fields in
    # the entities hash that would require additional API calls to resolve

    entities = {}
    entities['user_mentions'] = []
    for um in extractor.extract_mentioned_screen_names_with_indices():
        entities['user_mentions'].append(um)

    entities['hashtags'] = []
    for ht in extractor.extract_hashtags_with_indices():

        # massage field name to match production twitter api

        ht['text'] = ht['hashtag']
        del ht['hashtag']
        entities['hashtags'].append(ht)

    entities['urls'] = []
    for url in extractor.extract_urls_with_indices():
        entities['urls'].append(url)

    return entities


# Fetch a tweet using an API method of your choice and mixin the entities

t = twitter.Twitter(domain='api.twitter.com', api_version='1')

tweet = t.statuses.show(id=TWEET_ID)

tweet['entities'] = getEntities(tweet)

print json.dumps(tweet, indent=4)
