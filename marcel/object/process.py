# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, (or at your
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

import psutil

import marcel.object.error
import marcel.exception
import marcel.object.renderable
import marcel.util


Proc = psutil.Process  # Avoid confusion with marcel.object.process.Process


class Process(marcel.object.renderable.Renderable):

    def __init__(self, proc):
        assert type(proc) is Proc
        self.__dict__.update(proc.info)

    def __hash__(self):
        return self.pid

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
    def command(self):
        return '' if self.cmdline is None else ' '.join(self.cmdline)

    def signal(self, signal):
        os.kill(self.pid, signal)

    # Renderable

    def render_compact(self):
        return f'process({self.pid})'

    def render_full(self, color_scheme):
        pid = '{:6n}'.format(self.pid)
        ppid = '{:6n}'.format(self.ppid)
        user = '{:8s}'.format(self.username)
        status = '{:10s}'.format(self.status)
        command = self.command
        if color_scheme:
            pid = marcel.util.colorize(pid, color_scheme.process_pid)
            ppid = marcel.util.colorize(ppid, color_scheme.process_ppid)
            user = marcel.util.colorize(user, color_scheme.process_user)
            status = marcel.util.colorize(status, color_scheme.process_status)
            command = marcel.util.colorize(self.command, color_scheme.process_command)
        buffer = [
            pid,
            ppid,
            user,
            status,
            command
        ]
        return '  '.join(buffer)
