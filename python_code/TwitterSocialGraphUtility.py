# -*- coding: utf-8 -*-

"""
TODOs (which would potentially result in updating code listings):
    * Handling httplib and urllib errors for I/O? Stuff like BadStatusLine, etc.


"""

import sys
import time
import getopt
import cPickle
import json
import twitter
import redis
import locale
from random import shuffle
from functools import partial

locale.setlocale(locale.LC_ALL, '')


def pp(_int):  # for nice number formatting
    return locale.format('%d', _int, True)


# XXX: requires > twitter 1.3.1 which is not currently available from easy_install but will be soon

from twitter.oauth_dance import oauth_dance


class TwitterSocialGraphUtility:

    """
    Interactively does the OAuth dance to enable access to Twitter APIs from a user account.
    Launces a web browser for user to authorize access and the interactively prompts for PIN.
    """

    def __init__(
        self,
        redis_host='localhost',
        redis_port=6379,
        redis_db=0,
        ):

        self._REDIS_DELIM = '$'
        self._redis = redis.Redis(host=redis_host, port=redis_port, db=redis_db)

        try:
            import psyco
            psyco.bind(self.resolveUserInfoForKeys)
            print 'Using psyco to compile resolveUserInfoForKeys method'
        except ImportError, e:
            pass  # psyco not installed

    def doTwitterAuth(self, consumer_key, consumer_secret):
        (oauth_token, oauth_token_secret) = self._redis.mget(['oauth_token',
                'oauth_token_secret'])
        if not oauth_token and not oauth_token_secret:
            try:
                (oauth_token, oauth_token_secret) = oauth_dance('this application'
                        , consumer_key, consumer_secret)
                self._redis.mset({'oauth_token': oauth_token, 'oauth_token_secret'
                                 : oauth_token_secret})
            except twitter.api.TwitterHTTPError, e:

                                                    # probably an invalid pin

                print 'Unable to perform authentication with OAuth. Aborting'
                raise e
        else:
            print 'Using previously stored OAuth tokens'

        self.twitter_api = twitter.Twitter(domain='api.twitter.com',
                api_version='1', auth=twitter.oauth.OAuth(oauth_token,
                oauth_token_secret, consumer_key, consumer_secret))

    def handleTwitterHTTPError(self, e, wait_period=1):
        if wait_period > 3600:  # 1 hour
            print 'Too many retries. Quitting.'
            raise e

        if e.e.code == 401:
            print 'Encountered 401 Error (Not Authorized)'
            print 'User %s is protecting their tweets. Skipping...' \
                % (screen_name, )
            return None
        elif e.e.code == 404:
            print 'Encountered 404 Error (Not Found)'
            print 'This might be because you tried to lookup a user or group of users but none of them exist or are all suspended'
            return None
        elif e.e.code in (502, 503):
            print 'Encountered %i Error. Will retry in %i seconds' % (e.e.code,
                    wait_period)
            time.sleep(wait_period)
            wait_period *= 1.5
            return wait_period
        elif self.twitter_api.account.rate_limit_status()['remaining_hits'] == 0:
            status = self.twitter_api.account.rate_limit_status()
            now = time.time()  # UTC
            when_rate_limit_resets = status['reset_time_in_seconds']  # UTC
            sleep_time = when_rate_limit_resets - now
            print 'Rate limit reached: sleeping for %i secs' % (sleep_time, )
            time.sleep(sleep_time)
            return 1
        else:
            raise e # BEst to handle this based on the specific issue

    # A template-like function that can get friends or followers depending on
    # the function passed into it via func.

    def _getFriendsOrFollowersUsingFunc(
        self,
        func,
        key_name,
        screen_name=None,
        limit=10000,
        ):

        cursor = -1
        ids = []
        while cursor != 0:
            wait_period = 1
            while True:
                try:
                    response = func(screen_name=screen_name, cursor=cursor)
                    if limit < 5000:  # default page size for social graph api calls
                        response['ids'] = (response['ids'])[:limit]
                    for _id in response['ids']:
                        self._redis.sadd(self.getRedisIdByScreenName(screen_name,
                                         key_name), _id)
                    ids.extend(response['ids'])
                    wait_period = 1
                    break
                except twitter.api.TwitterHTTPError, e:
                    wait_period = self.handleTwitterHTTPError(e, wait_period)
                    if wait_period is None:
                        break

            cursor = response['next_cursor']
            scard = self._redis.scard(self.getRedisIdByScreenName(screen_name,
                                      key_name))
            print '\tFetched %s %s for %s' % (scard, key_name, screen_name)
            if limit and len(ids) >= limit:
                break

            print 'Done. Fetched %s %s for %s' % (len(ids), key_name, screen_name)
            return ids

    def getFriends(self, **kw):
        return partial(self._getFriendsOrFollowersUsingFunc,
                       self.twitter_api.friends.ids, 'friend_ids')(**kw)

    def getFollowers(self, **kw):
        return partial(self._getFriendsOrFollowersUsingFunc,
                       self.twitter_api.followers.ids, 'follower_ids')(**kw)

    def freshenUserInfo(self, screen_names=[]):
        if not screen_names:
            screen_names = [k.split('$')[1] for k in
                            self._redis.keys('screen_name$*$info.json').split()]
        print 'Freshening info for %i users' % (len(screen_names), )
        self.getUserInfo(screen_names=screen_names, verbose=True)

    def resolveUserInfoForKeys(self, keys, dont_freshen=True):
        ids = []
        for key in keys:
            ids.extend(list(self._redis.smembers(key)))

        if dont_freshen:  # only resolve for objects that have not been fetched already
            existing_info = self._redis.mget([self.getRedisIdByUserId(_id,
                    'info.json') for _id in ids])

            remaining_ids = []
            idx = 0
            while idx < len(ids):
                if existing_info[idx] is None:
                    remaining_ids.append(ids[idx])
                idx += 1

            print 'Of %s total ids to resolve,' % (pp(len(ids)), ),
            print 'not freshening the %s that are already fetched. That leaves %s to go' \
                % (pp(len(ids) - len(remaining_ids)), pp(len(remaining_ids)))

        print 'Resolving user data for %i users' % (len(remaining_ids), )
        self.getUserInfo(user_ids=remaining_ids, verbose=True)
        print 'Done'

    def getUserInfo(
        self,
        screen_names=[],
        user_ids=[],
        verbose=False,
        sample=1.0,
        ):

        if not screen_names and not user_ids:
            raise RuntimeError('Missing required parameters for getUserInfo(self,screen_names=None, user_ids=None)'
                               )

        # sampling technique: randomize the lists and trim the length.

        if sample < 1.0:
            for lst in [screen_names, user_ids]:
                shuffle(lst)
                lst = lst[:int(len(lst) * sample)]

        info = []
        n_info = 0
        while len(screen_names) > 0 or len(user_ids) > 0:
            (screen_names_str, user_ids_str) = (','.join(screen_names[:100]),
                    ','.join([str(_id) for _id in user_ids[:100]]))
            (screen_names, user_ids) = (screen_names[100:], user_ids[100:])

            wait_period = 1
            while True:
                try:
                    response = []
                    response = \
                        self.twitter_api.users.lookup(screen_name=screen_names_str,
                            user_id=user_ids_str)
                    wait_period = 1
                    break
                except twitter.api.TwitterHTTPError, e:

                    wait_period = self.handleTwitterHTTPError(e, wait_period)
                    if wait_period is None:
                        break

            if type(response) is dict:  # Handle api quirk
                response = [response]

            if len(response) == 0:  # could have happened if the event of a 404 response
                continue

            self._redis.mset(dict([(self.getRedisIdByScreenName(r['screen_name'],
                             'info.json'), json.dumps(r)) for r in response]))
            self._redis.mset(dict([(self.getRedisIdByUserId(r['id'], 'info.json'
                             ), json.dumps(r)) for r in response]))

            info.extend(response)
            n_info += len(response)
            if verbose:
                print 'Fetched/updated info for a total of %i users' % (n_info, )
        return info

    # XXX: A heuristic to do the crawl in the order of people who have most followers first (A*-ish) could be interesting
    #      in here.

    def crawl(
        self,
        screen_names,
        user_ids=[],
        friends_limit=10000,
        followers_limit=10000,
        depth=1,
        friends_sample=1.0,
        followers_sample=1.0,
        ):

        # Given the possibility of getting a mixture of screen names and user ids, re-resolve all of the
        # user objects to screen names and keep the rest of the code simple and screen name centric.

        for screen_name in [i['screen_name'] for i in
                            self.getUserInfo(screen_names=screen_names,
                            user_ids=user_ids)]:
            friend_ids = self.getFriends(screen_name=screen_name,
                                         limit=friends_limit)
            follower_ids = self.getFollowers(screen_name=screen_name,
                    limit=followers_limit)
            if friend_ids:
                friends_info = self.getUserInfo(user_ids=friend_ids,
                        sample=friends_sample)
            else:
                friends_info = []
            if follower_ids:
                followers_info = self.getUserInfo(user_ids=follower_ids,
                        sample=followers_sample)
            else:
                followers_info = []
            next_queue = [u['screen_name'] for u in friends_info + followers_info]

            d = 1
            while d < depth:
                d += 1
                (queue, next_queue) = (next_queue, [])
                for _screen_name in queue:
                    friend_ids = self.getFriends(screen_name=_screen_name,
                            limit=friends_limit)
                    follower_ids = self.getFollowers(screen_name=_screen_name,
                            limit=followers_limit)
                    next_queue.extend(friend_ids + follower_ids)
                    self.getUserInfo(user_ids=next_queue)

    def getRedisIdByScreenName(self, screen_name, key_name):
        return 'screen_name' + self._REDIS_DELIM + screen_name \
            + self._REDIS_DELIM + key_name

    def getRedisIdByUserId(self, user_id, key_name):
        return 'user_id' + self._REDIS_DELIM + str(user_id) + self._REDIS_DELIM \
            + key_name

    def friendsFollowersSymmetry(self, screen_names):
        for screen_name in screen_names:
            n_friends = \
                self._redis.scard(self.getRedisIdByScreenName(screen_name,
                                  'friend_ids'))
            n_followers = \
                self._redis.scard(self.getRedisIdByScreenName(screen_name,
                                  'follower_ids'))

            n_friends_diff_followers = self._redis.sdiffstore('temp',
                    [self.getRedisIdByScreenName(screen_name, 'friend_ids'),
                    self.getRedisIdByScreenName(screen_name, 'follower_ids')])
            self._redis.delete('$temp')
            n_followers_diff_friends = self._redis.sdiffstore('temp',
                    [self.getRedisIdByScreenName(screen_name, 'follower_ids'),
                    self.getRedisIdByScreenName(screen_name, 'friend_ids')])
            self._redis.delete('$temp')
            n_friends_inter_followers = self._redis.sinterstore('temp',
                    [self.getRedisIdByScreenName(screen_name, 'follower_ids'),
                    self.getRedisIdByScreenName(screen_name, 'friend_ids')])
            self._redis.delete('$temp')

            print '-' * 50
            print '%s is following %s' % (screen_name, pp(n_friends))
            print '%s is being followed by %s' % (screen_name, pp(n_followers))
            print '%s of %s are not following %s back' \
                % (pp(n_friends_diff_followers), pp(n_followers), screen_name)
            print '%s of %s are not being followed back by %s' \
                % (pp(n_followers_diff_friends), pp(n_followers), screen_name)
            print '%s has %s mutual friends (followers who are also being followed)' \
                % (screen_name, pp(n_friends_inter_followers))
            print '-' * 50

    def friendsFollowersInCommon(self, screen_names):
        self._redis.sinterstore('temp$friends_in_common',
                                [self.getRedisIdByScreenName(screen_name,
                                'friend_ids') for screen_name in screen_names])
        self._redis.sinterstore('temp$followers_in_common',
                                [self.getRedisIdByScreenName(screen_name,
                                'follower_ids') for screen_name in screen_names])

        print '-' * 50
        print 'Friends in common for %s: %s' % (','.join(screen_names),
                pp(self._redis.scard('temp$friends_in_common')))
        print 'Followers in common for %s: %s' % (','.join(screen_names),
                pp(self._redis.scard('temp$followers_in_common')))
        print '-' * 50

    def analyze(self, screen_names, analysis_type):
        try:
            for at in analysis_type:
                methodToCall = getattr(self, at)
                methodToCall(screen_names)
        except AttributeError, e:
            print 'Invalid option for analysis type: %s. Exiting.' \
                % (analysis_type, )
            raise e

    def getJson(self, screen_names, json_opts=[]):
        all = {}
        for screen_name in screen_names:
            o = {}
            if 'info' in json_opts:
                o['info'] = \
                    json.loads(self._redis.get(self.getRedisIdByScreenName(screen_name,
                               'info.json')))
            if 'friend_ids' in json_opts:
                o['friend_ids'] = \
                    list(self._redis.smembers(self.getRedisIdByScreenName(screen_name,
                         'friend_ids')))
            if 'follower_ids' in json_opts:
                o['follower_ids'] = \
                    list(self._redis.smembers(self.getRedisIdByScreenName(screen_name,
                         'follower_ids')))
            all[screen_name] = o
        return json.dumps(all, sort_keys=True, indent=4)


# XXX: Provide a more comprehensive usage page and try to make it easy to run multiple options at the same time
#     such as crawling and then immediately doing an analyze without invoking the program again, etc.


def usage():
    print 'Example usage:'
    print '$ %s --consumer-key=key --consumer-secret=secret ' % (sys.argv[0], ) \
        + '--screen-names=timoreilly,barackobama --crawl --depth=1\n' \
        + 'Other options to try:\n' \
        + '\t--friends-limit=1000 --followers-limit=1000\n' \
        + '\t--analyze=friendsFollowersSymmetry,friendsFollowersInCommon --print-json=info,friend_ids,follower_ids --depth\n' \
        + "\t--friends-sample=0.5 --followers-sample=0.5 --freshen-user-info --resolve-info-for-keys='screen_name$timoreilly$follower_ids'"
    exit()


if __name__ == '__main__':

    try:
        (opts, args) = getopt.getopt(sys.argv[1:], '', [  # always required
                                                          # used to update each user's info (num followers, latest status, etc.)
                                                          # optionally, use --screen-names to restrict freshening
                                                          # defaults that can be overridden when crawling
                                                          # to trigger a crawl (collect friends/followers)
                                                          # used for reading data from disk and printing as json
                                                          # used for various kinds of analysis on data that's already collected
            'consumer-key=',
            'consumer-secret=',
            'freshen-user-info',
            'screen-names=',
            'user-ids=',
            'friends-limit=',
            'followers-limit=',
            'friends-sample=',
            'followers-sample=',
            'depth=',
            'resolve-info-for-keys=',
            'crawl',
            'print-json=',
            'analyze=',
            ])
    except getopt.GetoptError, e:

            # print help information and exit:

        print str(e)  # will print something like "option -a not recognized"
        usage()

    # defaults

    (consumer_key, consumer_secret) = (None, None)
    (screen_names, user_ids) = ([], [])
    (friends_limit, followers_limit) = (10000, 10000)
    (friends_sample, followers_sample) = (1.0, 1.0)
    (do_print_json, do_crawl, do_freshen_user_info) = (False, False, False)
    resolve_info_for_keys = []
    analysis_type = None
    depth = 1
    json_opts = []

    for (o, a) in opts:
        if o == '--consumer-key':
            consumer_key = a
        elif o == '--consumer-secret':
            consumer_secret = a
        elif o == '--screen-names':
            screen_names = a.split(',')
        elif o == '--user-ids':
            user_ids = a.split(',')
        elif o == '--friends-limit':
            friends_limit = int(a)
        elif o == '--followers-limit':
            followers_limit = int(a)
        elif o == '--friends-sample':
            friends_sample = float(a)
        elif o == '--followers-sample':
            followers_sample = float(a)
        elif o == '--print-json':
            do_print_json = True
            json_opts = a.split(',')
        elif o == '--analyze':
            analysis_type = a.split(',')
        elif o == '--depth':
            depth = int(a)
        elif o == '--crawl':
            do_crawl = True
        elif o == '--freshen-user-info':
            do_freshen_user_info = True
        elif o == '--resolve-info-for-keys':
            resolve_info_for_keys = a.split(',')
        else:
            usage()

    tsgu = TwitterSocialGraphUtility()

    if do_print_json:
        print tsgu.getJson(screen_names, json_opts)
    elif analysis_type is not None:
        tsgu.analyze(screen_names, analysis_type)
    elif do_crawl:
        if consumer_key == None or consumer_secret == None:
            usage()
        if screen_names == [] and user_ids == []:
            usage()
        tsgu.doTwitterAuth(consumer_key, consumer_secret)
        tsgu.crawl(
            screen_names,
            user_ids,
            friends_limit,
            followers_limit,
            depth,
            friends_sample,
            followers_sample,
            )
    elif do_freshen_user_info:
        tsgu.doTwitterAuth(consumer_key, consumer_secret)
        tsgu.freshenUserInfo(screen_names)
    elif resolve_info_for_keys:
        tsgu.doTwitterAuth(consumer_key, consumer_secret)
        tsgu.resolveUserInfoForKeys(resolve_info_for_keys)
    else:
        print 'Nothing to do'
        usage()
