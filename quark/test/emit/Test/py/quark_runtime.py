# Quark Runtime
# Usage: from quark_runtime import *
# This brings in the stuff mentioned in __all__ below.
# The wrong way to do this, but minimizes the code change.

import os    # unused?
import sys
import time  # used by the builtin now() macro


__all__ = "os sys time _Map _List _println".split()


_Map = dict


class _List(list):
    def __repr__(self):
        return "[%s]" % ", ".join([str(e) for e in self])


def _println(obj):
    if obj is None:
        sys.stdout.write("null\n")
    else:
        sys.stdout.write("%s\n" % obj)