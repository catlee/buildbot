from zope.interface import implements
from asizeof import asizeof

from twisted.trial import unittest

from buildbot.changes.changes import Change
from buildbot import interfaces, util
from buildbot.process.properties import Properties

class OldChange:
    """I represent a single change to the source tree. This may involve
    several files, but they are all changed by the same person, and there is
    a change comment for the group as a whole.

    If the version control system supports sequential repository- (or
    branch-) wide change numbers (like SVN, P4, and Bzr), then revision=
    should be set to that number. The highest such number will be used at
    checkout time to get the correct set of files.

    If it does not (like CVS), when= should be set to the timestamp (seconds
    since epoch, as returned by time.time()) when the change was made. when=
    will be filled in for you (to the current time) if you omit it, which is
    suitable for ChangeSources which have no way of getting more accurate
    timestamps.

    The revision= and branch= values must be ASCII bytestrings, since they
    will eventually be used in a ShellCommand and passed to os.exec(), which
    requires bytestrings. These values will also be stored in a database,
    possibly as unicode, so they must be safely convertable back and forth.
    This restriction may be relaxed in the future.

    Changes should be submitted to ChangeMaster.addChange() in
    chronologically increasing order. Out-of-order changes will probably
    cause the web status displays to be corrupted."""

    implements(interfaces.IStatusEvent)

    number = None

    branch = None
    category = None
    revision = None # used to create a source-stamp

    def __init__(self, who, files, comments, isdir=0, links=None,
                 revision=None, when=None, branch=None, category=None,
                 revlink='', properties={}, repository='', project=''):
        self.who = who
        self.comments = comments
        self.isdir = isdir
        if links is None:
            links = []
        self.links = links

        def none_or_unicode(x):
            if x is None: return x
            return unicode(x)

        self.revision = none_or_unicode(revision)
        now = util.now()
        if when is None:
            self.when = now
        elif when > now:
            # this happens when the committing system has an incorrect clock, for example.
            # handle it gracefully
            log.msg("received a Change with when > now; assuming the change happened now")
            self.when = now
        else:
            self.when = when
        self.branch = none_or_unicode(branch)
        self.category = none_or_unicode(category)
        self.revlink = revlink
        self.properties = Properties()
        self.properties.update(properties, "Change")
        self.repository = repository
        self.project = project

        # keep a sorted list of the files, for easier display
        self.files = files[:]
        self.files.sort()

    def __setstate__(self, dict):
        self.__dict__ = dict
        # Older Changes won't have a 'properties' attribute in them
        if not hasattr(self, 'properties'):
            self.properties = Properties()
        if not hasattr(self, 'revlink'):
            self.revlink = ""

    def asText(self):
        data = ""
        data += self.getFileContents()
        if self.repository:
            data += "On: %s\n" % self.repository
        if self.project:
            data += "For: %s\n" % self.project
        data += "At: %s\n" % self.getTime()
        data += "Changed By: %s\n" % self.who
        data += "Comments: %s" % self.comments
        data += "Properties: \n%s\n\n" % self.getProperties()
        return data

    def asDict(self):
        '''returns a dictonary with suitable info for html/mail rendering'''
        result = {}

        files = []
        for file in self.files:
            link = filter(lambda s: s.find(file) != -1, self.links)
            if len(link) == 1:
                url = link[0]
            else:
                url = None
            files.append(dict(url=url, name=file))

        files = sorted(files, cmp=lambda a, b: a['name'] < b['name'])

        # Constant
        result['number'] = self.number
        result['branch'] = self.branch
        result['category'] = self.category
        result['who'] = self.getShortAuthor()
        result['comments'] = self.comments
        result['revision'] = self.revision
        result['rev'] = self.revision
        result['when'] = self.when
        result['at'] = self.getTime()
        result['files'] = files
        result['revlink'] = getattr(self, 'revlink', None)
        result['properties'] = self.properties.asList()
        result['repository'] = getattr(self, 'repository', None)
        result['project'] = getattr(self, 'project', None)
        return result

    def getShortAuthor(self):
        return self.who

    def getTime(self):
        if not self.when:
            return "?"
        return time.strftime("%a %d %b %Y %H:%M:%S",
                             time.localtime(self.when))

    def getTimes(self):
        return (self.when, None)

    def getText(self):
        return [html.escape(self.who)]
    def getLogs(self):
        return {}

    def getFileContents(self):
        data = ""
        if len(self.files) == 1:
            if self.isdir:
                data += "Directory: %s\n" % self.files[0]
            else:
                data += "File: %s\n" % self.files[0]
        else:
            data += "Files:\n"
            for f in self.files:
                data += " %s\n" % f
        return data

    def getProperties(self):
        data = ""
        for prop in self.properties.asList():
            data += "  %s: %s" % (prop[0], prop[1])
        return data

def makeChange(cls):
    params = dict(
            who='me', files=['file1', 'file2'], comments='comments',
            isdir=0, links=['link1', 'link2'], revision='123456', when=123455324,
            branch='branch1', category='category1', revlink='http://', properties={'prop1': 'value'},
            repository='repo', project='project')
    return cls(**params)

class TestChangeSize(unittest.TestCase):
    def test_change_size(self):
        old = asizeof(makeChange(OldChange))
        new = asizeof(makeChange(Change))
        self.assert_(new < old,
                "asizeof(Change) = %s; asizeof(OldChange) = %s" % (new, old))

if __name__ == '__main__':
    print "old:", asizeof(makeChange(OldChange))
    print "new:", asizeof(makeChange(Change))
