# -*- coding: utf-8 -*-

import oauth2 as oauth
import oauth2.clients.imap as imaplib

OAUTH_TOKEN = ''  # obtained with xoauth.py
OAUTH_TOKEN_SECRET = ''  # obtained with xoauth.py
GMAIL_ACCOUNT = ''  # example@gmail.com

url = 'https://mail.google.com/mail/b/%s/imap/' % (GMAIL_ACCOUNT, )

consumer = oauth.Consumer('anonymous', 'anonymous')  # Standard values for GMail's Xoauth
token = oauth.Token(OAUTH_TOKEN, OAUTH_TOKEN_SECRET)

conn = imaplib.IMAP4_SSL('imap.googlemail.com')
conn.debug = 4  # set to the desired debug level
conn.authenticate(url, consumer, token)

conn.select('INBOX')

# access your INBOX data
