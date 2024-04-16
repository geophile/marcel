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
import sys

import marcel.argsparser
import marcel.core
import marcel.exception

HELP = '''
{L,wrap=F}trace
{L,wrap=F}trace -s|--stdout
{L,wrap=F}trace -f|--file FILE
{L,wrap=F}trace -o|--off

{L,indent=4:28}{r:-s}, {r:--stdout}            Write trace output to stdout.

{L,indent=4:28}{r:-f}, {r:--file}              Write trace output to the specified FILE. 

{L,indent=4:28}{r:-o}, {r:--off}               Do not product trace output. 

Writes data tracing marcel execution to stdout or a file.

With no arguments, {r:trace} describes whether tracing is enabled, and if so,
where trace output is being written.

{r:--stdout} causes trace output to be written to the console.

{r:--file} causes trace output to be written to the specified {r:FILE}, appending
if the file already exists.

{r:--off} turns off tracing.

These arguments are all mutually exclusive.
'''


def trace(stdout=False, file=None, off=False):
    args = []
    if stdout:
        args.append('--stdout')
    if file:
        args.append('--file')
        args.append(file)
    if off:
        args.append('--off')
    return Trace(), args


class TraceArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('trace', env)
        self.add_flag_no_value('stdout', '-s', '--stdout')
        self.add_flag_one_value('file', '-f', '--file', target='filename')
        self.add_flag_no_value('off', '-o', '--off')
        self.at_most_one('stdout', 'file', 'off')
        self.validate()


class Trace(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.stdout = False
        self.filename = None
        self.off = False

    def __repr__(self):
        buffer = ['trace(']
        if self.stdout:
            buffer.append('stdout')
        if self.filename:
            buffer.append(self.filename)
        if self.off:
            buffer.append('off')
        buffer.append(')')
        return ''.join(buffer)

    # AbstractOp

    def run(self, env):
        if self.off:
            env.trace.disable()
        elif self.stdout:
            env.trace.enable(sys.stdout)
        elif self.filename:
            env.trace.enable(self.filename)
        else:
            env.trace.print_status()

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True
