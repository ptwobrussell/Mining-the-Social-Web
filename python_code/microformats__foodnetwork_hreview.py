# -*- coding: utf-8 -*-

import sys
import re
import urllib2
import json
import HTMLParser
from BeautifulSoup import BeautifulSoup

##################################################################################
# Warning: As of mid-Dec 2010, FoodNetwork.com seems to no longer include 
# hReview info for their recipes. This is likely a temporary deployment or
# development error. A support request is pending.
##################################################################################


# Pass in a URL such as
# http://www.foodnetwork.com/recipes/alton-brown/pad-thai-recipe/reviews/index.html

url = sys.argv[1]

# Parse out some of the pertinent information for a review
# from the Food Network's website
# See http://microformats.org/wiki/hreview


def parse_hreviews(url):
    try:
        page = urllib2.urlopen(url)
    except urllib2.URLError, e:
        print 'Failed to fetch ' + url
        raise e

    try:
        soup = BeautifulSoup(page)
    except HTMLParser.HTMLParseError, e:
        print 'Failed to parse ' + url
        raise e

    hreviews = soup.findAll(True, 'hreview')

    all_hreviews = []
    for hreview in hreviews:
        if hreview and len(hreview) > 1:
            item = hreview.find(True, 'item').find(text=True)
            summary = hreview.find(True, 'summary').string
            reviewer = hreview.find(True, 'reviewer')  # hCard
            dtreviewed = hreview.find(True, 'dtreviewed').string
            rating = hreview.find(True, 'rating').string
            description = hreview.find(True, 'description').string

            reviewer_name = reviewer.find(True, 'fn').string

            # these fields may not exist if the reviewer is Anonymous

            try:
                reviewer_locality = reviewer.find(True, 'locality').string
            except AttributeError, e:
                reviewer_locality = None
            try:
                reviewer_region = reviewer.find(True, 'region').string
            except AttributeError, e:
                reviewer_region = None

            all_hreviews.append({
                'item': item,
                'summary': summary,
                'reviewer': {'name': reviewer_name, 'locality'
                             : reviewer_locality, 'region': reviewer_region},
                'date_reviewed': dtreviewed,
                'rating': rating,
                'description': description,
                })
    return all_hreviews


reviews = parse_hreviews(url)
print json.dumps(reviews, indent=4)
