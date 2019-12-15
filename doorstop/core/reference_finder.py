# SPDX-License-Identifier: LGPL-3.0-only

"""Finding external references."""

import os
import re
import linecache

import time

from doorstop import common, settings
from doorstop.common import DoorstopError

log = common.logger(__name__)

class SimpleProfiler:

    def __init__(self):
        self.total_time = 0
        self.iterations = 0
        self.current_time = 0
        self.min_time = 1000
        self.max_time = -1000

    def start_timer(self):
        self.current_time = time.clock()

    def end_time(self):
        exec_time = time.clock() - self.current_time
        self.min_time = min(exec_time, self.min_time)
        self.max_time = max(exec_time, self.max_time)
        self.total_time += exec_time
        self.iterations += 1

    def display_stats(self, title):
        print(title)
        print("\tIterations:", self.iterations)
        print("\tTotal Time:", self.total_time)
        print("\tMax:", self.max_time)
        print("\tMin:", self.min_time)
        print("\tAvg:", self.total_time/self.iterations)



class ReferenceFinder:
    """Finds files referenced from an Item."""

    @staticmethod
    def find_ref(ref, tree, item_path):
        """Get the external file reference and line number.

        :raises: :class:`~doorstop.common.DoorstopError` when no
            reference is found

        :return: relative path to file or None (when no reference
            set),
            line number (when found in file) or None (when found as
            filename) or None (when no reference set)

        """
        profiler = SimpleProfiler()
        # Search for the external reference
        log.debug("searching for ref '{}'...".format(ref))
        pattern = r"(\b|\W){}(\b|\W)".format(re.escape(ref))
        log.trace("regex: {}".format(pattern))  # type: ignore
        regex = re.compile(pattern)
        for path, filename, relpath in tree.vcs.paths:
            # Skip the item's file while searching
            if path == item_path:
                continue
            # Check for a matching filename
            if filename == ref:
                return relpath, None
            # Skip extensions that should not be considered text
            if os.path.splitext(filename)[-1] in settings.SKIP_EXTS:
                continue
            # Search for the reference in the file
            profiler.start_timer()
            lineno = 1
            while True:
                try:
                    line = linecache.getline(path, lineno)
                except UnicodeDecodeError:
                    break
                except SyntaxError:
                    break
                if line == '':
                    break
                if regex.search(line):
                    log.debug("found ref: {}".format(relpath))
                    profiler.end_time()
                    profiler.display_stats(f"Stats for: {item_path}")
                    return relpath, lineno
                lineno += 1
            profiler.end_time()
        profiler.display_stats(f"Stats for: {item_path}")
        msg = "external reference not found: {}".format(ref)
        raise DoorstopError(msg)

    @staticmethod
    def find_file_reference(ref_path, root, tree, item_path, keyword=None):
        """Find the external file reference.

        :raises: :class:`~doorstop.common.DoorstopError` when no
            reference is found

        :return: Tuple (ref_path, line) when reference is found

        """

        log.debug("searching for ref '{}'...".format(ref_path))
        ref_full_path = os.path.join(root, ref_path)

        for path, filename, relpath in tree.vcs.paths:
            # Skip the item's file while searching
            if path == item_path:
                continue
            if path == ref_full_path:
                if keyword is None:
                    return relpath, None

                # Search for the reference in the file
                log.debug("searching for ref '{}'...".format(keyword))
                pattern = r"(\b|\W){}(\b|\W)".format(re.escape(keyword))
                log.trace("regex: {}".format(pattern))  # type: ignore
                regex = re.compile(pattern)
                lineno = 1
                while True:
                    try:
                        line = linecache.getline(path, lineno)
                    except UnicodeDecodeError:
                        break
                    except SyntaxError:
                        break
                    if line == '':
                        break
                    if regex.search(line):
                        log.debug("found ref: {}".format(relpath))
                        return relpath, lineno
                    lineno += 1

        msg = "external reference not found: {}".format(ref_path)
        raise DoorstopError(msg)
