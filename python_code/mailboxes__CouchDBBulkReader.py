# -*- coding: utf-8 -*-

from datetime import datetime as dt
from math import ceil
import httplib
import urllib
import time
import threadpool
try:
    import jsonlib2 as json
except:
    import json


class CouchDBBulkReader:

    def __init__(
        self,
        db,
        num_threads,
        host='localhost',
        port=5984,
        ):

        self.db = db
        self.num_threads = num_threads
        self.host = host
        self.port = port
        self.results = []

        id_buckets = self._getDocIds()
        self.pool = threadpool.ThreadPool(self.num_threads)
        requests = threadpool.makeRequests(self._getDocs, id_buckets,
                self._callback, self._errCallback)
        [self.pool.putRequest(req) for req in requests]
        self.pool.wait()

    def read(self):
        while True:
            try:
                time.sleep(0.5)
                self.pool.poll()
            except threadpool.NoResultsPending:
                return self.results
            except KeyboardInterrupt:
                print 'Keyboard interrupt. Exiting'
                sys.exit()
            finally:
                self.pool.joinAllDismissedWorkers()

    # Called to quickly get all of the document ids which can be sorted and dibbied out

    def _getDocIds(self):

        # Helper function to tersely compute a list of indices that evenly distribute
        # the items in it

        def partition(alist, indices):
            return [alist[i:j] for (i, j) in zip([0] + indices, indices
                    + [None])][:-1]

        try:
            conn = httplib.HTTPConnection(self.host, self.port)
            conn.request('GET', '/%s/_all_docs' % (self.db, ))
            response = conn.getresponse()
            if response.status != 200:  #  OK
                print 'Unable to get docs: %s %s' % (response.status,
                        response.reason)
                sys.exit()

            ids = [i['id'] for i in json.loads(response.read())['rows']
                   if not i['id'].startswith('_')]
            ids.sort()
        finally:
            conn.close()

        partition_size = int(ceil(1.0 * len(ids) / self.num_threads))
        indices = []

        _len = len(ids)
        idx = 0
        while idx < _len:
            idx += partition_size
            indices.append(idx)

        return partition(ids, indices)

    def _getDocs(self, ids):
        try:
            (startkey, endkey) = (ids[0], ids[-1])
            conn = httplib.HTTPConnection(self.host, self.port)
            conn.request('GET',
                         '/%s/_all_docs?startkey="%s"&endkey="%s"&include_docs=true'
                          % (self.db, startkey, endkey))
            response = conn.getresponse()
            if response.status != 200:  #  OK
                print 'Unable to get docs: %s %s' % (response.status,
                        response.reason)
                sys.exit()
            return response.read()
        finally:
            conn.close()

    def _errCallback(self, request, result):
        print 'An Error occurred:', request, result
        sys.exit()

    def _callback(self, request, result):
        rows = json.loads(result)['rows']
        self.results.extend([row['doc'] for row in rows])


