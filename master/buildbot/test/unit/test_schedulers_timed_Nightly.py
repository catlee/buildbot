import time

from twisted.trial import unittest
from twisted.internet import defer

from buildbot.schedulers import timed
from buildbot.changes.manager import ChangeManager
from buildbot.changes.changes import Change

class FakeDB:
    def __init__(self):
        self.schedulers = []
        self.changes = []
        self.sourcestamps = []
        self.scheduler_states = {}
        self.classified_changes = {}

    def addSchedulers(self, schedulers):
        i = len(self.schedulers)
        for s in schedulers:
            self.schedulers.append(s)
            s.schedulerid = i
            i += 1
        return defer.succeed(True)

    def addChangeToDatabase(self, change):
        i = len(self.changes)
        self.changes.append(change)
        change.number = i

    def get_sourcestampid(self, ss, t):
        i = len(self.sourcestamps)
        self.sourcestamps.append(ss)
        ss.ssid = ss
        return i

    def runInteraction(self, f, *args):
        return f(None, *args)

    def scheduler_get_state(self, schedulerid, t):
        return self.scheduler_states.get(schedulerid, {"last_processed": 0, "last_build": time.time()+100})

    def scheduler_set_state(self, schedulerid, t, state):
        self.scheduler_states[schedulerid] = state

    def getLatestChangeNumberNow(self, t):
        return len(self.changes)-1

    def getChangesGreaterThan(self, last_changeid, t):
        return self.changes[last_changeid:]

    def scheduler_get_classified_changes(self, schedulerid, t):
        return self.classified_changes.get(schedulerid, ([], []))

    def scheduler_classify_change(self, schedulerid, changeid, important, t):
        if schedulerid not in self.classified_changes:
            self.classified_changes[schedulerid] = ([], [])

        if important:
            self.classified_changes[schedulerid][0].append(self.changes[changeid])
        else:
            self.classified_changes[schedulerid][1].append(self.changes[changeid])

    def scheduler_retire_changes(self, schedulerid, changeids, t):
        if schedulerid not in self.classified_changes:
            return
        for c in self.classified_changes[schedulerid][0][:]:
            if c.number in changeids:
                self.classified_changes[schedulerid][0].remove(c)
        for c in self.classified_changes[schedulerid][1][:]:
            if c.number in changeids:
                self.classified_changes[schedulerid][1].remove(c)

    def create_buildset(self, *args):
        pass

class DummyParent:
    def __init__(self, dbconn):
        self.db = dbconn
        self.change_svc = ChangeManager()
        self.change_svc.parent = self

    def publish_buildset(self, name, bsid, t):
        pass


class Nightly(unittest.TestCase):
    def setUp(self):
        self.dbc = FakeDB()

    def test_dont_create_scheduler_changes(self):
        s = timed.Nightly(
                name="tsched",
                builderNames=['tbuild'])
        s.parent = DummyParent(self.dbc)

        d = self.dbc.addSchedulers([s])

        # Add some changes
        for i in range(10):
            c = Change(who='just a guy', files=[], comments="")
            d.addCallback(lambda res: self.dbc.addChangeToDatabase(c))

        def runScheduler(res):
            return s.run()
        d.addCallback(runScheduler)

        def checkTables(res):
            # Check that we have the number of changes we think we should have
            self.assertEquals(len(self.dbc.changes), 10)

            # Check that there are no entries in scheduler_changes
            important, unimportant = self.dbc.classified_changes.get(s.schedulerid, ([], []))
            self.assertEquals(len(important+unimportant), 0)
        d.addCallback(checkTables)
        return d

    def test_create_scheduler_changes(self):
        s = timed.Nightly(
                name="tsched",
                builderNames=['tbuild'],
                onlyIfChanged=True)
        s.parent = DummyParent(self.dbc)

        d = self.dbc.addSchedulers([s])

        # Add some changes
        for i in range(10):
            c = Change(who='just a guy', files=[], comments="")
            d.addCallback(lambda res: self.dbc.addChangeToDatabase(c))

        def runScheduler(res):
            return s.run()
        d.addCallback(runScheduler)

        def checkTables(res):
            # Check that we have the number of changes we think we should have
            self.assertEquals(len(self.dbc.changes), 10)

            # Check that there are entries in scheduler_changes
            important, unimportant = self.dbc.classified_changes.get(s.schedulerid, ([], []))
            self.assertEquals(len(important+unimportant), 10)
        d.addCallback(checkTables)
        return d

    def test_expire_old_scheduler_changes(self):
        s = timed.Nightly(
                name="tsched",
                builderNames=['tbuild'],
                )
        s.parent = DummyParent(self.dbc)

        # Hack the scheduler so that it always runs
        def _check_timer(t):
            now = time.time()
            s._maybe_start_build(t)
            s.update_last_build(t, now)

            # reschedule for the next timer
            return now + 10
        s._check_timer = _check_timer

        d = self.dbc.addSchedulers([s])

        # Add a changes
        c = Change(who='just a guy', files=[], comments="")
        d.addCallback(lambda res: self.dbc.addChangeToDatabase(c))

        # Add some dummy scheduler_changes
        def addSchedulerChanges(res):
            for i in range(100):
                self.dbc.classified_changes.setdefault(s.schedulerid, ([], []))[0].append(c)
        d.addCallback(addSchedulerChanges)

        def runScheduler(res):
            return s.run()
        d.addCallback(runScheduler)

        def checkTables(res):
            # Check that there are no entries in scheduler_changes
            important, unimportant = self.dbc.classified_changes.get(s.schedulerid, ([], []))
            self.assertEquals(len(important+unimportant), 0)
        d.addCallback(checkTables)
        return d
