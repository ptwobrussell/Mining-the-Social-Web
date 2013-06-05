# -*- coding: utf-8 -*-

import sys
import locale
import twitter
import redis
import json
import time
from random import shuffle
from urllib2 import URLError
from twitter__login import login

def makeTwitterRequest(twitterFunction, max_errors=3, *args, **kwArgs): 
    wait_period = 2
    error_count = 0

    while True:
        try:
            return twitterFunction(*args, **kwArgs)
        except twitter.api.TwitterHTTPError, e:
            error_count = 0
            wait_period = handleTwitterHTTPError(e, wait_period)
            if wait_period is None:
                return
        except URLError, e:
            error_count += 1
            print >> sys.stderr, "URLError encountered. Continuing."
            if error_count > max_errors:
                print >> sys.stderr, "Too many consecutive errors...bailing out."
                raise


# Handle the common HTTPErrors. Return an updated value for wait_period
# if the problem is a 503 error. Block until the rate limit is reset if
# a rate limiting issue
def handleTwitterHTTPError(e, wait_period=2, sleep_when_rate_limited=True):

    if wait_period > 3600: # Seconds
        print >> sys.stderr, 'Too many retries. Quitting.'
        raise e

    # See https://dev.twitter.com/docs/error-codes-responses for common codes

    if e.e.code == 401:
        print >> sys.stderr, 'Encountered 401 Error (Not Authorized)'
        return None
    elif e.e.code == 429: 
        print >> sys.stderr, 'Encountered 429 Error (Rate Limit Exceeded)'
        if sleep_when_rate_limited:
            print >> sys.stderr, "Sleeping for 15 minutes, and then I'll try again...ZzZ..."
            time.sleep(60*15 + 5)
            print >> sys.stderr, '...ZzZ...Awake now and trying again.'
            return 2
        else:
            raise e # Allow user to handle the rate limiting issue however they'd like 
    elif e.e.code in (502, 503):
        print >> sys.stderr, 'Encountered %i Error. Will retry in %i seconds' % (e.e.code,
                wait_period)
        time.sleep(wait_period)
        wait_period *= 1.5
        return wait_period
    else:
        raise e


# A template-like function that can get friends or followers depending on
# the function passed into it via func.

def _getFriendsOrFollowersUsingFunc(
    func,
    key_name,
    t, # Twitter connection
    r, # Redis connection
    screen_name=None,
    limit=10000,
    ):

    cursor = -1

    result = []
    while cursor != 0:
        response = makeTwitterRequest(func, screen_name=screen_name, cursor=cursor)
        for _id in response['ids']:
            result.append(_id)
            r.sadd(getRedisIdByScreenName(screen_name, key_name), _id)

        cursor = response['next_cursor']
        scard = r.scard(getRedisIdByScreenName(screen_name, key_name))
        print >> sys.stderr, 'Fetched %s ids for %s' % (scard, screen_name)
        if scard >= limit:
            break

    return result

def getUserInfo(
    t, # Twitter connection
    r, # Redis connection
    screen_names=[],
    user_ids=[],
    verbose=False,
    sample=1.0,
    ):

    # Sampling technique: randomize the lists and trim the length.

    if sample < 1.0:
        for lst in [screen_names, user_ids]:
            shuffle(lst)
            lst = lst[:int(len(lst) * sample)]

    info = []
    while len(screen_names) > 0:
        screen_names_str = ','.join(screen_names[:100])
        screen_names = screen_names[100:]

        response = makeTwitterRequest(t.users.lookup,
                                      screen_name=screen_names_str)
        
        if response is None:
            break
                                    
        if type(response) is dict:  # Handle api quirk
            response = [response]
        for user_info in response:
            r.set(getRedisIdByScreenName(user_info['screen_name'], 'info.json'),
                  json.dumps(user_info))
            r.set(getRedisIdByUserId(user_info['id'], 'info.json'), 
                  json.dumps(user_info))
        info.extend(response)

    while len(user_ids) > 0:
        user_ids_str = ','.join([str(_id) for _id in user_ids[:100]])
        user_ids = user_ids[100:]

        response = makeTwitterRequest(t.users.lookup,
                                      user_id=user_ids_str)
        
        if response is None:
            break
                                    
        if type(response) is dict:  # Handle api quirk
            response = [response]
        for user_info in response:
            r.set(getRedisIdByScreenName(user_info['screen_name'], 'info.json'),
                  json.dumps(user_info))
            r.set(getRedisIdByUserId(user_info['id'], 'info.json'), 
                  json.dumps(user_info))
        info.extend(response)


    return info


# Convenience functions

def pp(_int):  # For nice number formatting
    locale.setlocale(locale.LC_ALL, '')
    return locale.format('%d', _int, True)


def getRedisIdByScreenName(screen_name, key_name):
    return 'screen_name$' + screen_name + '$' + key_name


def getRedisIdByUserId(user_id, key_name):
    return 'user_id$' + str(user_id) + '$' + key_name

# For calculating the max_id parameter from statuses, which is 
# necessary in order to traverse a timeline in the v1.1 API. 
# See https://dev.twitter.com/docs/working-with-timelines

def getNextQueryMaxIdParam(statuses): 
    return min([ status['id'] for status in statuses ]) - 1

if __name__ == '__main__': # For ad-hoc testing

    t = login()

    # Test the flow for hitting the rate limit and pausing until
    # it's time to make another request on an arbitrary resource.
    # See https://dev.twitter.com/docs/rate-limiting/1.1/limits

    while True:
        resp = makeTwitterRequest(t.help.languages)
        print resp
        print resp.headers.items()
        print
