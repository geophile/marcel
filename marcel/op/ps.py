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

import functools
import os

import psutil

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.object.process
import marcel.util

Proc = psutil.Process  # Avoid name collision with marcel.object.process.Process

PROC_ATTRS = ['cmdline',
              'cpu_percent',
              'cpu_times',
              'create_time',
              'cwd',
              'environ',
              'exe',
              'gids',
              'memory_info',
              'name',
              'pid',
              'ppid',
              'status',
              'username',
              'uids']

HELP = '''
{L,wrap=F}ps [-u|--user [USER]] [-g|--group [GROUP]] [-p|--pid PID] [-c|--command STRING]

{L,indent=4:28}{r:-u}, {r:--user}              Report only processes owned by the specified USER.

{L,indent=4:28}{r:-g}, {r:--group}             Report only processes owned by the specified GROUP.

{L,indent=4:28}{r:-p}, {r:--pid}               Report only the process with the specified PID.

{L,indent=4:28}{r:-c}, {r:--command}           Report only the processes whose command line contains the specified STRING.

Generate a stream of {n:Process} objects, representing processes. If no arguments are provided,
then all processes, from all users, are reported. Otherwise, the processes are filtered based on the provided
flag.

At most one of the flags can be specified. For more complex selection criteria, run {r:ps} with no
arguments to obtain all {n:Process}es, and then use the {n:select} operator to specify an arbitrary filtering
condition, based on the attributes of {n:Process} objects. (Run {n:help process} for more information on
{n:Process} objects.)

If {r:--user} is specified, and {r:USER} is omitted, then the processes owned by the current user
are provided. Similarly, if {r:--group} is specified and {r:GROUP} is omitted, then the processes
owned by the current user's group are provided.

Users and groups can be identified by name, or by numeric id. In the latter case, real, effective and saved
ids are checked. E.g. {n:ps -u 1002} would return processes in which the real uid, effective uid, or saved
uid is 1002.

If {r:--command} is specified, then the {r:STRING} argument is matched against the process name,
executable name, and command line.
'''


class Uninitialized:
    pass


_UNINITIALIZED = Uninitialized()


def ps(env, user=_UNINITIALIZED, group=_UNINITIALIZED, pid=_UNINITIALIZED, command=_UNINITIALIZED):
    op = Ps(env)
    op.user = user
    op.group = group
    op.pid = pid
    op.command = command
    return op


class PsArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('ps', env)
        self.add_flag_optional_value('user', '-u', '--user', convert=self.check_str, target='user_arg')
        self.add_flag_optional_value('group', '-g', '--group', convert=self.check_str, target='group_arg')
        self.add_flag_one_value('pid', '-p', '--pid', convert=self.check_str, target='pid_arg')
        self.add_flag_one_value('command', '-c', '--command', convert=self.check_str, target='command_arg')
        self.at_most_one('user', 'group', 'pid', 'command')
        self.validate()


class Ps(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.user_arg = _UNINITIALIZED
        self.user = None
        self.group_arg = _UNINITIALIZED
        self.group = None
        self.pid_arg = _UNINITIALIZED
        self.pid = None
        self.command_arg = _UNINITIALIZED
        self.command = None
        self.filter = None

    def __repr__(self):
        return f'Process({self.pid})'

    # AbstractOp

    def setup(self):
        self.user = self.eval_function('user_arg', int, str)
        self.group = self.eval_function('group_arg', int, str)
        self.pid = self.eval_function('pid_arg', int)
        self.command = self.eval_function('command_arg', str)
        # user, group can be name or id. A name can be numeric, and in that case, the name interpretation
        # takes priority. Convert name to uid, since that is a cheaper lookup on a Project.
        # If user or group is None, no user/group was specified, so use this user/group.
        # A value of type Uninitialized means it wasn't specified at all.
        #
        # user can be True if -u is specified with no value.
        self.filter = lambda p: True
        if type(self.user) is not Uninitialized:
            self.user = os.getuid() if self.user in (None, True) else Ps.convert_to_id(self.user, marcel.util.uid)
            self.filter = lambda p: self.user in p.uids
        if type(self.group) is not Uninitialized:
            self.group = os.getgid() if self.group in (None, True) else Ps.convert_to_id(self.group, marcel.util.gid)
            self.filter = lambda p: self.group in p.gids
        if type(self.pid) is not Uninitialized:
            try:
                self.pid = int(self.pid)
                self.filter = lambda p: self.pid == p.pid
            except ValueError:
                raise marcel.exception.KillCommandException(f'pid must be an int: {self.pid}')
        if type(self.command) is not Uninitialized:
            self.filter = (lambda p: p.name is not None and self.command in p.name or
                                     p.exe is not None and self.command in p.exe or
                                     p.cmdline is not None and functools.reduce(lambda x, y: x or y,
                                                                                [self.command in x for x in p.cmdline],
                                                                                False))

    def receive(self, _):
        for proc in psutil.process_iter(PROC_ATTRS):
            process = marcel.object.process.Process(proc)
            if self.filter(process):
                self.send(process)

    # Op

    def must_be_first_in_pipeline(self):
        return True

    # For use by this class

    @staticmethod
    def convert_to_id(name, lookup):
        id = lookup(name)
        if id is None:
            try:
                id = int(name)
            except ValueError:
                pass
        if id is None:
            raise marcel.exception.KillCommandException(f'{name} is not a recognized id or name.')
        return id
