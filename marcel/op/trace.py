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
{L,wrap=F}trace -0|--off
{L,wrap=F}trace -1|--on
{L,wrap=F}trace -f|--file FILE

{L,indent=4:28}{r:-0}, {r:--off}               Do not produce trace output. 

{L,indent=4:28}{r:-1}, {r:--on}                Write trace output to stdout.

{L,indent=4:28}{r:-f}, {r:--file}              Write trace output to the specified {r:FILE.} 

Writes data tracing marcel execution to stdout or a file.

With no arguments, {r:trace} describes whether tracing is enabled, and if so,
where trace output is being written.

{r:--on} causes trace output to be written to stdout.

{r:--off} turns off tracing.

{r:--file} causes trace output to be written to the specified {r:FILE}, appending
if the file already exists.

These arguments are all mutually exclusive.
'''


def trace(off=False, on=False, file=None):
    args = []
    if off:
        args.append('--off')
    if on:
        args.append('--on')
    if file:
        args.append('--file')
        args.append(file)
    return Trace(), args


class TraceArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('trace', env)
        self.add_flag_no_value('off', '-0', '--off')
        self.add_flag_no_value('on', '-1', '--on')
        self.add_flag_one_value('file', '-f', '--file', target='filename')
        self.at_most_one('on', 'off', 'file')
        self.validate()


class Trace(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.off = False
        self.on = False
        self.filename = None

    def __repr__(self):
        buffer = ['trace(']
        if self.on:
            buffer.append('on')
        if self.off:
            buffer.append('off')
        if self.filename:
            buffer.append(self.filename)
        buffer.append(')')
        return ''.join(buffer)

    # AbstractOp

    def run(self, env):
        if self.off:
            env.trace.disable()
        elif self.on:
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
