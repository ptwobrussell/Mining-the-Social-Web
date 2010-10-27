# -*- coding: utf-8 -*-


def pp(_int):  # for nice number formatting
    return locale.format('%d', _int, True)


def friendsFollowersInCommon(screen_names):
    r.sinterstore('temp$friends_in_common', [getRedisIdByScreenName(screen_name,
                  'friend_ids') for screen_name in screen_names])
    r.sinterstore('temp$followers_in_common',
                  [getRedisIdByScreenName(screen_name, 'follower_ids')
                  for screen_name in screen_names])

    print '-' * 50
    print 'Friends in common for %s: %s' % (','.join(screen_names),
            pp(r.scard('temp$friends_in_common')))
    print 'Followers in common for %s: %s' % (','.join(screen_names),
            pp(r.scard('temp$followers_in_common')))
    print '-' * 50

    # clean up scratch workspace

    r.delete('temp$friends_in_common')
    r.delete('temp$followers_in_common')


