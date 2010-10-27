# -*- coding: utf-8 -*-

from random import shuffle


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


def getUserInfo(
    screen_names=[],
    user_ids=[],
    verbose=False,
    sample=1.0,
    ):

    # sampling technique: randomize the lists and trim the length.

    if sample < 1.0:
        for lst in [screen_names, user_ids]:
            shuffle(lst)
            lst = lst[:int(len(lst) * sample)]

    info = []
    while len(screen_names) > 0 or len(user_ids) > 0:
        (screen_names_str, user_ids_str) = (','.join(screen_names[:100]),
                ','.join([str(_id) for _id in user_ids[:100]]))
        (screen_names, user_ids) = (screen_names[100:], user_ids[100:])

        wait_period = 2
        while True:
            try:
                response = twitter_api.users.lookup(screen_name=screen_names_str,
                        user_id=user_ids_str)
                wait_period = 2
                break
            except twitter.api.TwitterHTTPError, e:
                wait_period = handleTwitterHTTPError(e)
                if wait_period is None:
                    break

        if type(response) is dict:  # Handle api quirk
            response = [response]
        for r in response:
            r.set(getRedisIdByScreenName(r['screen_name'], 'info.json'),
                  json.dumps(r))
            r.set(getRedisIdByUserId(r['id'], 'info.json'), json.dumps(r))
        info.extend(response)
    return info


def crawl(
    screen_names,
    friends_limit=10000,
    followers_limit=10000,
    depth=1,
    friends_sample=1.0,
    followers_sample=1.0,
    ):

    getUserInfo(screen_names=screen_names)
    for screen_name in screen_names:
        (friend_ids, follower_ids) = \
            getFriendsAndFollowers(screen_name=screen_name,
                                   friends_limit=friends_limit,
                                   followers_limit=followers_limit)
        friends_info = getUserInfo(user_ids=friend_ids, sample=friends_sample)
        followers_info = getUserInfo(user_ids=follower_ids,
                                     sample=followers_sample)
        next_queue = [u['screen_name'] for u in friends_info + followers_info]

        d = 1
        while d < depth:
            d += 1
            (queue, next_queue) = (next_queue, [])
            for _screen_name in queue:
                (friend_ids, follower_ids) = \
                    getFriendsAndFollowers(screen_name=_screen_name,
                        friends_limit=friends_limit,
                        followers_limit=followers_limit)
                next_queue.extend(friend_ids + follower_ids)
                getUserInfo(user_ids=next_queue)


