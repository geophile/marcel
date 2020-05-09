# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or at your
# option) any later version.
# 
# Marcel is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Marcel.  If not, see <https://www.gnu.org/licenses/>.

"""Provides information on currently running processes, by examining files in the C{/proc} filesystem.
(So it doesn't work on OS X, for example.) The C{processes} function returns a list of C{Process}
objects. Each C{Process} object reveals information derived from C{/proc}, identifies
parent and child processes, and can be used to send signals to the process.
"""

import os
import os.path
import pathlib

import marcel.object.renderable


def processes(*dummy):
    """Returns a list of process objects based on the current contents of C{/proc}.
    Of course the list is stale as soon as it is formed. In particular, a C{Process}
    object in the list may correspond to a process that has terminated by the time
    you use the object.
    """
    process_list = []
    for file in os.listdir('/proc'):
        if file.isdigit():
            process_list.append(Process(int(file)))
    return process_list


class Process(marcel.object.renderable.Renderable):
    """A C{Process} object represents a process with a particular PID. The process may or may not
    be running when the C{Process} object is used. It is conceivable that the C{Process} object
    does not represent the same process that was identified by the PID when the C{Process} object
    was created.
    """

    def __init__(self, pid):
        """Creates a C{Process} object for a given C{pid}. For internal use only.
        """
        self._pid = pid
        self._status = self._read_status_file()
        self._descendents = None
        if self._status is not None:
            self._init_parent()
            self._init_state()
            self._init_commandline()
            self._init_env()
            self._init_size()
            self._init_rss()

    def __repr__(self):
        return self.render_compact()

    def __hash__(self):
        return self._pid

    def __eq__(self, other):
        return self.pid == other.pid

    def __ne__(self, other):
        return self.pid != other.pid

    def __lt__(self, other):
        return self.pid < other.pid

    def __le__(self, other):
        return self.pid <= other.pid

    def __gt__(self, other):
        return self.pid > other.pid

    def __ge__(self, other):
        return self.pid >= other.pid

    # Process

    exists = property(lambda self: self._status is not None)

    pid = property(lambda self: self._pid,
                   doc='The PID of this C{Process}.')

    parent = property(lambda self: self._parent, 
                      doc='The parent of this C{Process}. Returns a C{Process} object.')

    state = property(lambda self: self._state, 
                     doc='The state of this C{Process}.')

    size = property(lambda self: self._size, 
                    doc='The VM size of this C{Process}.')

    rss = property(lambda self: self._rss, 
                   doc='The VM RSS of this C{Process}.')

    commandline = property(lambda self: self._commandline, 
                           doc='The command-line used to create this C{Process}.')

    env = property(lambda self: self._env, 
                   doc='A map describing the environment in effect during the creation of this C{Process}.')

    descendents = property(lambda self: self._find_descendents())

    def kill(self, signal):
        """Send the indicated C{signal} to this process.
        """
        os.kill(self._pid, signal)

    # Renderable

    def render_compact(self):
        return f'process({self.pid})'

    def render_full(self, color_scheme):
        pid = '{:6n}'.format(self.pid)
        commandline = self.commandline
        if color_scheme:
            pid = marcel.util.colorize(pid, color_scheme.process_pid)
            commandline = marcel.util.colorize(commandline, color_scheme.process_commandline)
        buffer = [
            '--' if self._status is None else '  ',
            pid,
            commandline
        ]
        return ' '.join(buffer)

    # For use by this class

    def _find_descendents(self):
        if self._descendents is None:
            processes = set()
            for file in os.listdir('/proc'):
                if file.isdigit():
                    processes.add(Process(int(file)))
            descendents = set()
            descendents.add(self)
            more = True
            while more:
                more = False
                for p in processes:
                    if p.exists and p._parent in descendents and p not in descendents:
                        descendents.add(p)
                        more = True
            descendents.remove(self)
            self._descendents = list(descendents)
        return self._descendents

    def _read_status_file(self):
        try:
            with open((self._procdir() / 'status').as_posix(), 'r') as status_file:
                status = status_file.readlines()
            status_map = {}
            for key_value_string in status:
                colon = key_value_string.find(':')
                key = key_value_string[:colon].strip()
                value = key_value_string[colon + 1:].strip()
                status_map[key] = value
            return status_map
        except IOError:
            return None

    def _strings_file(self, filename):
        strings = []
        try:
            with open((self._procdir() / filename).as_posix(), 'r') as file:
                contents = file.read()
            strings = contents.split(chr(0))
        except IOError:
            pass
        return strings

    def _procdir(self):
        return pathlib.Path('/proc') / str(self._pid)

    def _init_parent(self):
        self._parent = Process(int(self._status['PPid']))

    def _init_state(self):
        self._state = self._status['State'].split()[0]

    def _init_commandline(self):
        commandline_tokens = [x for x in self._strings_file('cmdline') if len(x) > 0]
        self._commandline = ' '.join(commandline_tokens) if commandline_tokens else ''

    def _init_env(self):
        env_map = self._strings_file('environ')
        self._env = {}
        for key_value_string in env_map:
            eq = key_value_string.find('=')
            key = key_value_string[:eq].strip()
            value = key_value_string[eq + 1:].strip()
            if key:
                self._env[key] = value

    def _init_size(self):
        self._size = self._size_in_bytes('VmSize')

    def _init_rss(self):
        self._size = self._size_in_bytes('VmRSS')

    def _size_in_bytes(self, label):
        size = self._status.get(label, None)
        if size is not None:
            space = size.find(' ')
            assert size[space + 1:].lower() == 'kb'
            size = int(size[:space])  # chop off kB
            return size * 1024  # multiply by kB
        else:
            return 0
