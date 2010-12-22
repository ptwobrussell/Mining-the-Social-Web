# -*- coding: utf-8 -*-

import re
import email
from time import asctime
import os
import sys
from dateutil.parser import parse  # easy_install dateutil

directory = sys.argv[1]

for (root, dirs, file_names) in os.walk(directory):

    if root.split(os.sep)[-1].lower() != 'inbox':
        continue

    for file_name in file_names:
        file_path = os.path.join(root, file_name)
        message_text = open(file_path).read()

    # compute fields for the From_ line in a traditional mbox message

        _from = re.search(r"From: ([^\r]+)", message_text).groups()[0]
        _date = re.search(r"Date: ([^\r]+)", message_text).groups()[0]

    # convert _date to the asctime representation for the From_ line

        _date = asctime(parse(_date).timetuple())

        msg = email.message_from_string(message_text)
        msg.set_unixfrom('From %s %s' % (_from, _date))
        print msg.as_string(unixfrom=True)
        print
        # redirect stdout to a file, or write to a file directly
