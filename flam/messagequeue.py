# encoding: utf-8
#
# Copyright (C) 2008-2009 Alec Thomas <alec@swapoff.org
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# Author: Alec Thomas <alec@swapoff.org>

"""A persistent message queue."""

from __future__ import with_statement

import cPickle as pickle

from directory_queue.directory_queue import DirectoryQueue
from directory_queue.generic_queue_item import GenericQueueItem


__all__ = ['Message', 'Queue']


class Message(object):
    """A message extracted from the message queue.

    :attr data: Message payload.
    """

    def __init__(self, dq, item):
        self._dq = dq
        self._item = item
        self._data = None

    @property
    def data(self):
        """Message payload."""
        if self._data is None:
            with open(self._item.dataFileName(), 'r') as f:
                self._data = pickle.load(f)
        return self._data

    def done(self):
        """Mark message as done."""
        self._dq.itemDone(self._item)

    def delete(self):
        """Delete message from queue."""
        self._dq.itemDelete(self._item)

    def error(self):
        """Send message to the error queue."""
        self._dq.itemError(self._item)

    def requeue(self):
        """Requeue the message for processing."""
        self._dq.itemRequeue(self._item)


class Queue(object):
    """A persistent message queue."""

    def __init__(self, directory):
        """Create a new queue.

        :param directory: Root directory of queue.
        """
        self._directory = directory
        self._dq = DirectoryQueue(directory, GenericQueueItem)

    def put(self, payload):
        """Put an object into the queue.

        :param payload: Python object (will be pickled) to insert into the
                        queue.
        """
        item = self._dq.newQueueItem('flam')
        try:
            with open(item.dataFileName(), 'w') as f:
                pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
            self._dq.itemReady(item)
        except:
            try:
                self._dq.itemDelete(item)
            except:
                pass
            raise

    def get(self):
        """Extract data from the queue.

        :returns: None or a Message object.
        """
        try:
            item = self._dq.getNext()
        except OSError:
            return None
        if item:
            try:
                return Message(self, item)
            except:
                self._dq.itemRequeue(item)
                raise
        return None
