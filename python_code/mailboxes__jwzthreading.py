# -*- coding: utf-8 -*-

"""
Overview: Contains an implementation of an algorithm for threading mail
messages, as described at http://www.jwz.org/doc/threading.html.

License: This code was minimally adapted and touched up from the Mail Trends
source code - http://code.google.com/p/mail-trends/ - under the
Apache 2.0 License

TODOs: Clean this code up more. It was pretty gnarly as originally yanked
     and still needs some work.
"""

import sys
import re
import mailbox
import email
import json


class Container:

    def __init__(self):
        self.message = self.parent = None
        self.children = []
        self.subject = None

    def __repr__(self):
        return '<%s %x: %r>' % (self.__class__.__name__, id(self), self.message)

    def is_dummy(self):
        return self.message is None

    def add_child(self, child):
        if child.parent:
            child.parent.remove_child(child)
        self.children.append(child)
        child.parent = self

    def remove_child(self, child):
        self.children.remove(child)
        child.parent = None

    def has_descendant(self, ctr):
        if self is ctr:
            return True
        for c in self.children:
            if c is ctr:
                return True
            elif c.has_descendant(ctr):
                return True
        return False

    def __len__(self):
        count = 1
        for c in self.children:
            count += len(c)
        return count

    @staticmethod
    def display(ctr, depth=0, debug=1):
        sys.stdout.write(depth * ' ')
        if debug:

            # Printing the repr() is more useful for debugging

            sys.stdout.write(repr(ctr))
        else:
            sys.stdout.write(repr(ctr.message and ctr.message.subject))

        sys.stdout.write('\n')
        for c in ctr.children:
            display(c, depth + 1)

    @staticmethod
    def flatten(ctr, debug=0):

        if ctr.message and not ctr.children:
            result = [{'external_id': ctr.message.external_id}]
            if debug:
                result[0]['subject'] = ctr.message.subject
            return result

        result = []
        for c in ctr.children:
            result += Container.flatten(c, debug)

        return result

    @staticmethod
    def prune(container):
        """Container.prune(container:Container) : [Container]
        Recursively prune a tree of containers, as described in step 4
        of the algorithm.  Returns a list of the children that should replace
        this container.
        """

        # Prune children, assembling a new list of children

        new_children = []
        for ctr in container.children[:]:
            L = Container.prune(ctr)
            new_children.extend(L)
            container.remove_child(ctr)

        for c in new_children:
            container.add_child(c)

        if container.message is None and len(container.children) == 0:

            # 4.A: nuke empty containers

            return []
        elif container.message is None and (len(container.children) == 1
                or container.parent is not None):

            # 4.B: promote children

            L = container.children[:]
            for c in L:
                container.remove_child(c)
            return L
        else:

            # Leave this node in place

            return [container]


class Message(object):

    def __init__(self, msg, external_id='_id'):
        """
        Create a Message object for threading purposes from a JSONified 
        RFC822 message.
        """

        self.message_id = None
        self.subject = ''
        self.references = []
        self.external_id = msg[external_id]

        # Message ID

        msgid_pat = re.compile('<([^>]+)>')
        m = msgid_pat.search(msg.get('Message-ID', ''))
        if m is None:
            return

        self.message_id = m.group(1)

        # Get list of unique message IDs from the References: header

        self.references = list(set(msgid_pat.findall(msg.get('References', ''))))

        # Get In-Reply-To: header and add it to references

        in_reply_to = msg.get('In-Reply-To', '')
        m = msgid_pat.search(in_reply_to)
        if m:
            msg_id = m.group(1)
            if msg_id not in self.references:
                self.references.append(msg_id)

        # Subject

        self.subject = msg.get('Subject', 'No subject')


def thread(msglist):
    """thread([Message]) : {string:Container}

    The main threading function.  This takes a list of Message
    objects, and returns a dictionary mapping subjects to Containers.
    Containers are trees, with the .children attribute containing a
    list of subtrees, so callers can then sort children by date or
    poster or whatever.
    """

    id_table = {}
    for msg in msglist:

        # 1A

        this_container = id_table.get(msg.message_id, None)
        if this_container is not None:
            this_container.message = msg
        else:
            this_container = Container()
            this_container.message = msg
            id_table[msg.message_id] = this_container

        # 1B

        prev = None
        for ref in msg.references:
            container = id_table.get(ref, None)
            if container is None:
                container = Container()
                container.message_id = ref
                id_table[ref] = container

            if prev is not None:

                # Don't add link if it would create a loop

                if container is this_container:
                    continue
                if container.has_descendant(prev):
                    continue
                prev.add_child(container)

            prev = container

        if prev is not None:
            prev.add_child(this_container)

    # 2. Find root set

    root_set = [container for container in id_table.values() if container.parent
                is None]

    # 3. Delete id_table

    del id_table

    # 4. Prune empty containers

    for container in root_set:
        assert container.parent == None

    new_root_set = []
    for container in root_set:
        L = Container.prune(container)
        new_root_set.extend(L)

    root_set = new_root_set

    # 5. Group root set by subject

    restrip_pat = \
        re.compile("""(
          (Re(\[\d+\])?:) | (\[ [^]]+ \])
        \s*)+
        """,
                   re.I | re.VERBOSE)

    subject_table = {}
    for container in root_set:
        if container.message:
            subj = container.message.subject
        else:
            subj = container.children[0].message.subject

        subj = restrip_pat.sub('', subj)
        if subj == '':
            continue

        existing = subject_table.get(subj, None)
        if existing is None or existing.message is not None and container.message \
            is None or existing.message is not None and container.message \
            is not None and len(existing.message.subject) \
            > len(container.message.subject):
            subject_table[subj] = container

    # 5C

    for container in root_set:
        if container.message:
            subj = container.message.subject
        else:
            subj = container.children[0].message.subject

        subj = restrip_pat.sub('', subj)
        ctr = subject_table.get(subj)
        if ctr is None or ctr is container:
            continue
        if ctr.is_dummy() and container.is_dummy():
            for c in ctr.children:
                container.add_child(c)
        elif ctr.is_dummy() or container.is_dummy():
            if ctr.is_dummy():
                ctr.add_child(container)
            else:
                container.add_child(ctr)
        elif len(ctr.message.subject) < len(container.message.subject):

            # ctr has fewer levels of 're:' headers

            ctr.add_child(container)
        elif len(ctr.message.subject) > len(container.message.subject):

            # container has fewer levels of 're:' headers

            container.add_child(ctr)
        else:
            new = Container()
            new.add_child(ctr)
            new.add_child(container)
            subject_table[subj] = new

    return [Container.flatten(container, debug=1) for (subj, container) in
            subject_table.items()]


