from zope.interface import implements
from asizeof import asizeof

from twisted.trial import unittest

from buildbot.status.builder import Event
from buildbot import interfaces

class OldEvent:
    implements(interfaces.IStatusEvent)

    def __init__(self):
        self.started = None
        self.finished = None
        self.text = []

    # IStatusEvent methods
    def getTimes(self):
        return (self.started, self.finished)
    def getText(self):
        return self.text
    def getLogs(self):
        return []

    def finish(self):
        self.finished = util.now()

class TestEventSize(unittest.TestCase):
    def test_event_size(self):
        new = asizeof(Event())
        old = asizeof(OldEvent())
        self.assert_(new < old,
                "asizeof(Event) = %s; asizeof(OldEvent) = %s" % (new, old))

if __name__ == '__main__':
    print "old:", asizeof(OldEvent())
    print "new:", asizeof(Event())
