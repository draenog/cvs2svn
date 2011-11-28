import cPickle
import cStringIO
import datetime
import sys
import re

class NotesCreator:
    def __init__(self):
        self.dates = {}
        self.logs = {}
        self.metadata_id = {}
        self.changing_rev = {}

        self._firstlinepattern = re.compile(r'^# \$''Revision:(.*)\$, \$''Date:(.*)\$')
        self._datepattern = re.compile(r'^%define[\t ]*date[\t ]*.%\(echo')
        self._revpattern = re.compile(r'^Revision\s*(\S+)')



    def process_spec(self,fulltext, revision, timestamp, metadata_id):
        inp = cStringIO.StringIO(fulltext)
        out = cStringIO.StringIO()
#Skip to changelog
        for line in inp:
            if self._firstlinepattern.match(line):
                continue
            if self._datepattern.match(line):
                break
            out.write(line)
# Parse changelog
        revpattern = re.compile(r'Revision\s*(\S+)')
        rev = None
        log = ''
        for line in inp:
            _m = self._revpattern.match(line)
            if _m:
                if rev:
                    self.store(rev, revision, timestamp, log, metadata_id)
                    log = ''
                rev = _m.group(1)
                continue
            if rev:
                log += line
        self.store(rev, revision, timestamp, log, metadata_id)

        return out.getvalue().rstrip('\n') + '\n'

    def store(self, rev, ch_revision, timestamp, log, metadata_id):
        log = log.rstrip() + '\n'
        if rev not in self.dates:
            self.dates[rev] = timestamp
            self.logs[rev] = log
            self.metadata_id[rev] = metadata_id
            self.changing_rev[rev] = ch_revision
        elif self.dates[rev] < timestamp and self.logs[rev] != log:
            self.dates[rev] = timestamp
            self.logs[rev] = log
            self.metadata_id[rev] = metadata_id
            self.changing_rev[rev] = ch_revision
        elif self.dates[rev] > timestamp and self.logs[rev] == log:
            self.dates[rev] = timestamp
            self.metadata_id[rev] = metadata_id
            self.changing_rev[rev] = ch_revision



    def dump_notes(self, dump):
        cPickle.dump(self.dates, dump)
        cPickle.dump(self.logs, dump)
        cPickle.dump(self.metadata_id, dump)
        cPickle.dump(self.changing_rev, dump)


    def load_notes(self, dump):
        self.dates = cPickle.load(dump)
        self.logs = cPickle.load(dump)
        self.metadata_id = cPickle.load(dump)
        self.changing_rev = cPickle.load(dump)
