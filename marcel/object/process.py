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

import os
import os.path
import pathlib

import marcel.exception
import marcel.object.renderable
import marcel.util


def processes(*dummy):
    process_list = []
    for file in os.listdir('/proc'):
        if file.isdigit():
            process_list.append(Process(int(file)))
    return process_list


class Process(marcel.object.renderable.Renderable):

    def __init__(self, pid):
        self._pid = pid
        self._ppid = None
        self._uid = None
        self._gid = None
        self._state = None
        self._commandline = None
        self._env = None
        # Contents of files under /proc
        self._status = None
        self._cmdline = None
        self._environ = None

    def __repr__(self):
        return self.render_compact()

    def __getattr__(self, attr):
        self._ensure_status()
        return self._status.get(attr, None)

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

    @property
    def pid(self):
        return self._pid

    @property
    def ppid(self):
        self._ensure_status()
        return self._ppid
    
    @property
    def uid(self):
        self._ensure_status()
        return self._uid
    
    @property
    def user(self):
        self._ensure_status()
        return None if self._uid is None else marcel.util.username(self._uid)

    @property
    def gid(self):
        self._ensure_status()
        return self._gid

    @property
    def group(self):
        self._ensure_status()
        return None if self._gid is None else marcel.util.groupname(self._gid)

    @property
    def state(self):
        self._ensure_status()
        return self._state

    @property
    def commandline(self):
        self._ensure_cmdline()
        return self._commandline

    @property
    def env(self):
        self._ensure_environ()
        return self._env

    def signal(self, signal):
        os.kill(self._pid, signal)

    # Renderable

    def render_compact(self):
        return f'process({self.pid})'

    def render_full(self, color_scheme):
        if not self._exists():
            raise Exception(f'Process {self.pid} does not exist.')
        pid = '{:6n}'.format(self.pid)
        ppid = '{:6n}'.format(self.ppid)
        user = '{:8s}'.format(self.user)
        state = '{}'.format(self.state)
        commandline = self.commandline
        if color_scheme:
            pid = marcel.util.colorize(pid, color_scheme.process_pid)
            ppid = marcel.util.colorize(ppid, color_scheme.process_ppid)
            user = marcel.util.colorize(user, color_scheme.process_user)
            state = marcel.util.colorize(state, color_scheme.process_state)
            commandline = marcel.util.colorize(commandline, color_scheme.process_commandline)
        buffer = [
            '--' if self._exists() is None else '  ',
            pid,
            ppid,
            user,
            state,
            commandline
        ]
        return '  '.join(buffer)

    # For use by this class

    def _ensure_status(self):
        if self._status is None:
            try:
                with open((self._procdir() / 'status').as_posix(), 'r') as status_file:
                    status_lines = status_file.readlines()
                self._status = {}
                for key_value in status_lines:
                    colon = key_value.find(':')
                    if colon != -1:
                        key = key_value[:colon].strip()
                        value = key_value[colon + 1:].strip()
                        self._status[key] = value
                    # else: Shouldn't happen in a proc file
                # Take care of major bits of state cached in self
                v = self._status.get('State', None)
                if v is not None:
                    self._state = v[0]  # E.g., "S (sleeping)"
                v = self._status.get('PPid', None)
                if v is not None:
                    self._ppid = int(v)
                v = self._status.get('Uid')
                if v is not None:
                    self._uid = int(v.split()[1])  # Effective uid
                v = self._status.get('Gid')
                if v is not None:
                    self._gid = int(v.split()[1])  # Effective gid
            except IOError:
                pass

    def _ensure_cmdline(self):
        if self._commandline is None:
            commandline_tokens = [x for x in self._strings_file('cmdline') if len(x) > 0]
            self._commandline = ' '.join(commandline_tokens) if commandline_tokens else ''

    def _ensure_environ(self):
        if self._environ is None:
            env_map = self._strings_file('environ')
            self._env = {}
            for key_value_string in env_map:
                eq = key_value_string.find('=')
                key = key_value_string[:eq].strip()
                value = key_value_string[eq + 1:].strip()
                if key:
                    self._env[key] = value

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

    def _exists(self):
        self._ensure_status()
        return self._status is not None

    # Should get rid of this, but needed by farcel

    def descendents(self):
        processes = {}  # pid -> Process
        for file in os.listdir('/proc'):
            if file.isdigit():
                process = Process(int(file))
                processes[process.pid] = process
        descendents = set()
        descendents.add(self)
        more = True
        while more:
            more = False
            for child in processes.values():
                parent = processes.get(child.pid, None)
                if parent:
                    if parent in descendents and child not in descendents:
                        descendents.add(child)
                        more = True
        descendents.remove(self)
        return descendents
