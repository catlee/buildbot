import os, shutil

from twisted.trial import unittest

from buildbot.schedulers import basic
from buildbot.db.schema import manager
from buildbot.db import dbspec, connector

from mock import Mock

class TestPriority(unittest.TestCase):
    def setUp(self):
        self.basedir = "TestPriority"
        if os.path.exists(self.basedir):
            shutil.rmtree(self.basedir)
        os.makedirs(self.basedir)

        self.spec = dbspec.DBSpec.from_url("sqlite:///state.sqlite", self.basedir)
        self.dbc = connector.DBConnector(self.spec)

        self.sm = manager.DBSchemaManager(self.spec, self.basedir)
        self.sm.upgrade()
        self.dbc.start()

    def testDefaultPriority(self):
        s = basic.Scheduler(
                name='tsched',
                branch=None,
                treeStableTimer=60,
                builderNames=['tbuild'])

        s.parent = Mock()
        s.parent.db = self.dbc

        def create_buildset(t):
            s.create_buildset(1, "my reason", t)
            return t
        d = self.dbc.runInteraction(create_buildset)

        def check(t):
            requests = self.dbc.runQueryNow(
                    "SELECT priority, buildername FROM buildrequests")
            self.failUnlessEquals(len(requests), 1)
            r = requests[0]
            self.failUnlessEquals(r, (0, 'tbuild'))
        d.addCallback(check)

        return d

    def testIntPriority(self):
        s = basic.Scheduler(
                name='tsched',
                branch=None,
                treeStableTimer=60,
                builderNames=['tbuild', 'tbuild2'],
                priority=1)

        s.parent = Mock()
        s.parent.db = self.dbc

        def create_buildset(t):
            s.create_buildset(1, "my reason", t)
            return t
        d = self.dbc.runInteraction(create_buildset)

        def check(t):
            requests = self.dbc.runQueryNow(
                    "SELECT priority, buildername FROM buildrequests")
            self.failUnlessEquals(len(requests), 2)
            r = requests[0]
            self.failUnlessEquals(r, (1, 'tbuild'))
            r = requests[1]
            self.failUnlessEquals(r, (1, 'tbuild2'))
        d.addCallback(check)

        return d

    def testCallablePriority(self):
        def priorityFunc(ssid, reason, properties, bn, t):
            self.failUnlessEquals(ssid, 1)
            self.failUnlessEquals(reason, "my reason")
            self.failUnlessEquals(bn, "tbuild3")
            return 2

        s = basic.Scheduler(
                name='tsched',
                branch=None,
                treeStableTimer=60,
                builderNames=['tbuild3'],
                priority=priorityFunc)

        s.parent = Mock()
        s.parent.db = self.dbc

        def create_buildset(t):
            s.create_buildset(1, "my reason", t)
            return t
        d = self.dbc.runInteraction(create_buildset)

        def check(t):
            requests = self.dbc.runQueryNow(
                    "SELECT priority, buildername FROM buildrequests")
            self.failUnlessEquals(len(requests), 1)
            r = requests[0]
            self.failUnlessEquals(r, (2, 'tbuild3'))
        d.addCallback(check)

        return d
