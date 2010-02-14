# (Be in -*- python -*- mode.)
#
# ====================================================================
# Copyright (c) 2007 CollabNet.  All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.  The terms
# are also available at http://subversion.tigris.org/license-1.html.
# If newer versions of this license are posted there, you may use a
# newer version instead, at your option.
#
# This software consists of voluntary contributions made by many
# individuals.  For exact contribution history, see the revision
# history and logs, available at http://cvs2svn.tigris.org/.
# ====================================================================

"""This module processes RCS diffs (deltas)."""


from cStringIO import StringIO
import re


def msplit(s):
  """Split S into an array of lines.

  Only \n is a line separator. The line endings are part of the lines."""

  # return s.splitlines(True) clobbers \r
  re = [ i + "\n" for i in s.split("\n") ]
  re[-1] = re[-1][:-1]
  if not re[-1]:
    del re[-1]
  return re


class MalformedDeltaException(Exception):
  """A malformed RCS delta was encountered."""

  pass


class RCSStream:
  """This class allows RCS deltas to be accumulated.

  This file holds the contents of a single RCS version in memory as an
  array of lines.  It is able to apply an RCS delta to the version,
  thereby transforming the stored text into the following RCS version.
  While doing so, it can optionally also return the inverted delta.

  This class holds revisions in memory.  It uses temporary memory
  space of a few times the size of a single revision plus a few times
  the size of a single delta."""

  ad_command = re.compile(r'^([ad])(\d+)\s(\d+)\n$')
  a_command = re.compile(r'^a(\d+)\s(\d+)\n$')

  def __init__(self, text):
    """Instantiate and initialize the file content with TEXT."""

    self._lines = msplit(text)

  def get_text(self):
    """Return the current file content."""

    return "".join(self._lines)

  def apply_diff(self, diff):
    """Apply the RCS diff DIFF to the current file content."""

    new_lines = []

    # The number of lines from the old version that have been
    # processed so far:
    ooff = 0

    diffs = msplit(diff)
    i = 0
    while i < len(diffs):
      admatch = self.ad_command.match(diffs[i])
      if not admatch:
        raise MalformedDeltaException('Bad ed command')
      i += 1
      start = int(admatch.group(2))
      count = int(admatch.group(3))
      if admatch.group(1) == 'd': # "d" - Delete command
        start -= 1
        if start < ooff:
          raise MalformedDeltaException('Deletion before last edit')
        if start > len(self._lines):
          raise MalformedDeltaException('Deletion past file end')
        if start + count > len(self._lines):
          raise MalformedDeltaException('Deletion beyond file end')
        # Copy the lines before the chunk to be deleted:
        new_lines += self._lines[ooff:start]
        ooff += start - ooff
        # Now skip over the lines to be deleted without appending them
        # to the output:
        ooff += count
      else: # "a" - Add command
        if start < ooff:
          raise MalformedDeltaException('Insertion before last edit')
        if start > len(self._lines):
          raise MalformedDeltaException('Insertion past file end')
        # Copy the lines before the chunk to be added:
        new_lines += self._lines[ooff:start]
        ooff += start - ooff
        # Now add the lines from the diff:
        new_lines += diffs[i:i + count]
        i += count
    self._lines = new_lines + self._lines[ooff:]

  def invert_diff(self, diff):
    """Apply the RCS diff DIFF to the current file content and simultaneously
    generate an RCS diff suitable for reverting the change."""

    new_lines = []

    # The number of lines from the old version that have been
    # processed so far:
    ooff = 0

    diffs = msplit(diff)
    inverse_diff = StringIO()
    adjust = 0
    i = 0
    while i < len(diffs):
      admatch = self.ad_command.match(diffs[i])
      if not admatch:
        raise MalformedDeltaException('Bad ed command')
      i += 1
      start = int(admatch.group(2))
      count = int(admatch.group(3))
      if admatch.group(1) == 'd': # "d" - Delete command
        start -= 1
        if start < ooff:
          raise MalformedDeltaException('Deletion before last edit')
        if start > len(self._lines):
          raise MalformedDeltaException('Deletion past file end')
        if start + count > len(self._lines):
          raise MalformedDeltaException('Deletion beyond file end')
        # Handle substitution explicitly, as add must come after del
        # (last add may end in no newline, so no command can follow).
        if i < len(diffs):
          amatch = self.a_command.match(diffs[i])
        else:
          amatch = None
        if amatch and int(amatch.group(1)) == start + count:
          count2 = int(amatch.group(2))
          i += 1
          inverse_diff.write("d%d %d\n" % (start + 1 + adjust, count2,))
          inverse_diff.write("a%d %d\n" % (start + adjust + count2, count,))
          inverse_diff.writelines(self._lines[start:start + count])
          # Copy over the lines that come before the substitution:
          new_lines += self._lines[ooff:start]
          ooff += start - ooff
          # Now add the lines from the diff:
          new_lines += diffs[i:i + count2]
          adjust += count2 - count
          i += count2
          # Now skip over the lines to be deleted without appending
          # them to the output:
          ooff += count
        else:
          inverse_diff.write("a%d %d\n" % (start + adjust, count))
          inverse_diff.writelines(self._lines[start:start + count])
          # Copy the lines before the chunk to be deleted:
          new_lines += self._lines[ooff:start]
          ooff += start - ooff
          adjust -= count
          # Now skip over the lines to be deleted without appending them
          # to the output:
          ooff += count
      else: # "a" - Add command
        if start < ooff: # Also catches same place
          raise MalformedDeltaException('Insertion before last edit')
        if start > len(self._lines):
          raise MalformedDeltaException('Insertion past file end')
        inverse_diff.write("d%d %d\n" % (start + 1 + adjust, count))
        # Copy the lines before the chunk to be added:
        new_lines += self._lines[ooff:start]
        ooff += start - ooff
        # Now add the lines from the diff:
        new_lines += diffs[i:i + count]
        adjust += count
        i += count
    self._lines = new_lines + self._lines[ooff:]
    return inverse_diff.getvalue()


