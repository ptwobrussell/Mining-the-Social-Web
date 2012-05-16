# -*- coding: utf-8 -*-

import sys
import mailbox
import email
import quopri
from BeautifulSoup import BeautifulSoup

try:
    import jsonlib2 as json  # much faster then Python 2.6.x's stdlib
except ImportError:
    import json

MBOX = sys.argv[1]
OUT_FILE = None
try:
    OUT_FILE = sys.argv[2]
except Exception, e:
    pass

def cleanContent(msg):

    # Decode message from "quoted printable" format

    msg = quopri.decodestring(msg)

    # Strip out HTML tags, if any are present

    soup = BeautifulSoup(msg)
    return ''.join(soup.findAll(text=True))


def jsonifyMessage(msg):
    json_msg = {'parts': []}
    for (k, v) in msg.items():
        json_msg[k] = v.decode('utf-8', 'ignore')

    # The To, CC, and Bcc fields, if present, could have multiple items
    # Note that not all of these fields are necessarily defined

    for k in ['To', 'Cc', 'Bcc']:
        if not json_msg.get(k):
            continue
        json_msg[k] = json_msg[k].replace('\n', '').replace('\t', '').replace('\r'
                , '').replace(' ', '').decode('utf-8', 'ignore').split(',')

    try:
        for part in msg.walk():
            json_part = {}
            if part.get_content_maintype() == 'multipart':
                continue
            json_part['contentType'] = part.get_content_type()
            content = part.get_payload(decode=False).decode('utf-8', 'ignore')
            json_part['content'] = cleanContent(content)

            json_msg['parts'].append(json_part)
    except Exception, e:
        sys.stderr.write('Skipping message - error encountered (%s)' % (str(e), ))
    finally:
        return json_msg

 #Note: opening in binary mode is recommended
 
 mbox = mailbox.UnixMailbox(open(MBOX, 'rb'), email.message_from_file)  
 def gen_json_msgs(m_box):
    while 1:
        msg = m_box.next()
        if msg is None:
            break
        yield jsonifyMessage(msg)
        
if OUT_FILE:
    json.dump(gen_json_msgs(mbox),open(OUT_FILE, 'wb'), indent=4)
else:
    print json.dumps(gen_json_msgs(mbox), indent=4)
