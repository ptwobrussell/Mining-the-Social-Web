# -*- coding: utf-8 -*-

import sys
import oauth2 as oauth
import oauth2.clients.imap as imaplib

# See http://code.google.com/p/google-mail-xoauth-tools/wiki/
#     XoauthDotPyRunThrough for details on xoauth.py

OAUTH_TOKEN = sys.argv[1]  # obtained with xoauth.py
OAUTH_TOKEN_SECRET = sys.argv[2]  # obtained with xoauth.py
GMAIL_ACCOUNT = sys.argv[3]  # example@gmail.com

url = 'https://mail.google.com/mail/b/%s/imap/' % (GMAIL_ACCOUNT, )

# Standard values for GMail's Xoauth
consumer = oauth.Consumer('anonymous', 'anonymous')  
token = oauth.Token(OAUTH_TOKEN, OAUTH_TOKEN_SECRET)

conn = imaplib.IMAP4_SSL('imap.googlemail.com')
conn.debug = 4  # set to the desired debug level
conn.authenticate(url, consumer, token)

conn.select('INBOX')

# access your INBOX data
