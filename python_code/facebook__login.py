# -*- coding: utf-8 -*-

import os
import sys
import webbrowser
import urllib


def login():

    # Get this value from your Facebook application's settings

    CLIENT_ID = ''

    REDIRECT_URI = 'http://miningthesocialweb.appspot.com/static/facebook_oauth_helper.html'

    # You could customize which extended permissions are being requested on the login 
    # page or by editing the list below. By default, all the ones that make sense for  
    # read access as described on http://developers.facebook.com/docs/authentication/ 
    # are included. (And yes, it would be probably be ridiculous to request this much 
    # access if you wanted to launch a successful production application.)

    EXTENDED_PERMS = [
        'user_about_me',
        'friends_about_me',
        'user_activities',
        'friends_activities',
        'user_birthday',
        'friends_birthday',
        'user_education_history',
        'friends_education_history',
        'user_events',
        'friends_events',
        'user_groups',
        'friends_groups',
        'user_hometown',
        'friends_hometown',
        'user_interests',
        'friends_interests',
        'user_likes',
        'friends_likes',
        'user_location',
        'friends_location',
        'user_notes',
        'friends_notes',
        'user_online_presence',
        'friends_online_presence',
        'user_photo_video_tags',
        'friends_photo_video_tags',
        'user_photos',
        'friends_photos',
        'user_relationships',
        'friends_relationships',
        'user_religion_politics',
        'friends_religion_politics',
        'user_status',
        'friends_status',
        'user_videos',
        'friends_videos',
        'user_website',
        'friends_website',
        'user_work_history',
        'friends_work_history',
        'email',
        'read_friendlists',
        'read_requests',
        'read_stream',
        'user_checkins',
        'friends_checkins',
        ]

    args = dict(client_id=CLIENT_ID, redirect_uri=REDIRECT_URI,
                scope=','.join(EXTENDED_PERMS), type='user_agent', display='popup'
                )

    webbrowser.open('https://graph.facebook.com/oauth/authorize?'
                    + urllib.urlencode(args))

    # Optionally, store your access token locally for convenient use as opposed
    # to passing it as a command line parameter into scripts...

    access_token = raw_input('Enter your access_token: ')

    if not os.path.isdir('out'):
        os.mkdir('out')

    filename = os.path.join('out', 'facebook.access_token')
    f = open(filename, 'w')
    f.write(access_token)
    f.close()

    print >> sys.stderr, \
            "Access token stored to local file: 'out/facebook.access_token'"

    return access_token

if __name__ == '__main__':
    login()
