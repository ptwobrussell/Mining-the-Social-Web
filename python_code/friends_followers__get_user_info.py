# -*- coding: utf-8 -*-

# Handle the common HTTPErrors. Return an updated value for wait_period
# if the problem is a 503 error. Block until the rate limit is reset if
# a rate limiting issue


def handleTwitterHTTPError(e, wait_period=2):
    if wait_period > 3600:  # 1 hour
        print 'Too many retries. Quitting.'
        raise e

    if e.e.code == 401:
        print 'Encountered 401 Error (Not Authorized)'
        print 'User %s is protecting their tweets. Skipping...' % (screen_name, )
        return None
    elif e.e.code in (502, 503):
        print 'Encountered %i Error. Will retry in %i seconds' % (e.e.code,
                wait_period)
        time.sleep(wait_period)
        wait_period *= 1.5
        return wait_period
    elif t.account.rate_limit_status()['remaining_hits'] == 0:
        status = t.account.rate_limit_status()
        now = time.time()  # UTC
        when_rate_limit_resets = status['reset_time_in_seconds']  # UTC
        sleep_time = when_rate_limit_resets - now
        print 'Rate limit reached: sleeping for %i secs' % (sleep_time, )
        time.sleep(sleep_time)
        return 2
    else:
        print 'Encountered unhandled error (%i). Trying again in %s secs' \
            % (e.e.code, wait_period)
        time.sleep(wait_period)
        wait_period *= 1.5
        return wait_period


def getRedisIdByScreenName(screen_name, key_name):
    return 'screen_name$' + screen_name + '$' + key_name


def getRedisIdByUserId(user_id, key_name):
    return 'user_id$' + str(user_id) + '$' + key_name


def getUserInfo(screen_names=[], user_ids=[]):
    while len(screen_names) > 0 or len(user_ids) > 0:
        (screen_names_str, user_ids_str) = (','.join(screen_names[:100]),
                ','.join([str(i) for i in user_ids[:100]]))
        (screen_names, user_ids) = (screen_names[100:], user_ids[100:])

        wait_period = 2
        while True:
            try:
                response = t.users.lookup(screen_name=screen_names_str,
                        user_id=user_ids_str)

                wait_period = 2
                break
            except twitter.api.TwitterHTTPError, e:
                wait_period = handleTwitterHTTPError(e, wait_period)
                if wait_period is None:
                    break

        if type(response) is dict:  # Handle api quirk
            response = [response]
        r.mset(dict([(getRedisIdByScreenName(resp['screen_name'], 'info.json'),
               json.dumps(resp)) for resp in response]))
        r.mset(dict([(getRedisIdByUserId(resp['id'], 'info.json'),
               json.dumps(resp)) for resp in response]))

        info.extend(response)


friends_not_following_back_ids = r.sdiff([getRedisIdByScreenName(screen_name,
                                         'friend_ids'),
                                         getRedisIdByScreenName(screen_name,
                                         'follower_ids')])
friends_not_following_back = \
    getUserInfo(screen_names=friends_not_following_back_ids)

# do something interesting with friends_not_following_back like print out the screen names
