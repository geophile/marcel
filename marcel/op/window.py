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

import types

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.util


HELP = '''
{L,wrap=F}window [-o|--overlap N] [-d|--disjoint N] [PREDICATE]

{L,indent=4:28}{r:-o}, {r:--overlap}           Generate overlapping windows of size N.

{L,indent=4:28}{r:-d}, {r:--disjoint}          Generate disjoint windows of size N.

{L,indent=4:28}{r:PREDICATE}               Start a new window on inputs for which the predicate
evaluates to True.

Groups of consecutive input tuples are combined into a single tuple, which is written to
the output stream. 

The objects are grouped using one of two
mechanisms.

{b:Predicate-based:}

A new group is started on the first input object, and for any
subsequent object for which {r:PREDICATE} returns true. For example, if
the input stream contains the integers {n:1, 2, 3, ...}, then:
{p,wrap=F}
    window (x: x % 3 == 2)

yields as output:
{p,wrap=F}
    1
    (2, 3, 4)
    (5, 6, 7)
    (8, 9, 10)
    ...

I.e., a new tuple is started for each integer n, (after the first integer) such that n % 3 = 2.

{b:Fixed-size}:

Groups have a fixed number of objects. The {r:--overlap} and {r:--disjoint} flags
specify {r:N}, the number of objects in the groups.  {r:--overlap}
specifies {i:overlapping} windows, in which each input object begins a
new list containing {r:N} items. Groups may be padded with
{r:None} values to ensure that the group's size is {r:N}.

{b:Example:}
 
For input {n:0, 1, ..., 9}, {r:window -o 3} yields these
tuples:
{p,wrap=F}
    (0, 1, 2)
    (1, 2, 3)
    (2, 3, 4)
    (3, 4, 5)
    (4, 5, 6)
    (5, 6, 7)
    (6, 7, 8)
    (7, 8, 9)
    (8, 9, None)
    (9, None, None)

{r:--disjoint} specifies {i:disjoint} windows, in which each input object
appears in only one group. A new group is started every {r:N}
objects. The last window may be padded with (None,) to ensure that it
has {r:N} elements.

{b:Example:}

For input {n:0, 1, ..., 9}, {r:window -d 3} yields these
tuples:
{p,wrap=F}
    (0, 1, 2)
    (3, 4, 5)
    (6, 7, 8)
    (9, None, None)
'''


def window(env, predicate=None, overlap=None, disjoint=None):
    args = []
    if overlap is not None:
        args.extend(['--overlap', overlap])
    if disjoint is not None:
        args.extend(['--disjoint', disjoint])
    if predicate:
        args.append(predicate)
    return Window(env), args


class WindowArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('window', env)
        self.add_flag_one_value('overlap', '-o', '--overlap', convert=self.str_to_int, target='overlap_arg')
        self.add_flag_one_value('disjoint', '-d', '--disjoint', convert=self.str_to_int, target='disjoint_arg')
        self.add_anon('predicate', convert=self.function, default=None)
        self.exactly_one('overlap', 'disjoint', 'predicate')
        self.validate()


class Window(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.predicate = None
        self.overlap_arg = None
        self.overlap = None
        self.disjoint_arg = None
        self.disjoint = None
        self.window_generator = None
        self.n = None

    def __repr__(self):
        buffer = ['window(']
        if self.overlap:
            buffer.append('overlap=')
            buffer.append(str(self.overlap))
        if self.disjoint:
            buffer.append('disjoint=')
            buffer.append(str(self.disjoint))
        if self.predicate:
            buffer.append('predicate=')
            buffer.append(self.predicate.source())
        buffer.append(')')
        return ''.join(buffer)

    # AbstractOp

    def setup(self):
        self.overlap = self.eval_function('overlap_arg', int)
        self.disjoint = self.eval_function('disjoint_arg', int)
        if self.predicate:
            self.window_generator = PredicateWindow(self)
        elif self.overlap:
            super().check_arg(type(self.overlap) is int and self.overlap >= 0,
                              'overlap', 'must be a non-negative int')
            self.window_generator = OverlapWindow(self)
            self.n = self.overlap
        else:  # disjoint
            super().check_arg(type(self.disjoint) is int and self.disjoint >= 0,
                              'disjoint', 'must be a non-negative int')
            self.window_generator = DisjointWindow(self)
            self.n = self.disjoint

    def set_env(self, env):
        super().set_env(env)
        if self.predicate:
            self.predicate.set_globals(env.vars())

    # Op

    def receive(self, x):
        self.window_generator.receive(x)

    def flush(self):
        if self.window_generator is not None:
            self.window_generator.flush()


class WindowBase:

    def __init__(self, op):
        self.op = op
        self.window = []

    def receive(self, x):
        assert False

    def flush(self):
        assert False

    def flush_window(self):
        if len(self.window) > 0:
            self.op.send(tuple(self.window))
            self.window = []


class PredicateWindow(WindowBase):

    def __init__(self, op):
        super().__init__(op)

    def receive(self, x):
        if self.op.call(self.op.predicate, *x):
            self.flush_window()
        self.window.append(marcel.util.unwrap_op_output(x))

    def flush(self):
        self.flush_window()
        self.op.propagate_flush()


class OverlapWindow(WindowBase):

    def __init__(self, op):
        super().__init__(op)

    def receive(self, x):
        if len(self.window) == self.op.n:
            self.window = self.window[1:]
        self.window.append(marcel.util.unwrap_op_output(x))
        if len(self.window) == self.op.n:
            self.op.send(tuple(self.window))

    def flush(self):
        if len(self.window) > 0:
            padding = None
            if len(self.window) < self.op.n:
                while len(self.window) < self.op.n:
                    self.window.append(padding)
                self.op.send(tuple(self.window))
            for i in range(self.op.n - 1):
                self.window = self.window[1:]
                self.window.append(padding)
                self.op.send(tuple(self.window))
            self.op.propagate_flush()


class DisjointWindow(WindowBase):

    def __init__(self, op):
        super().__init__(op)

    def receive(self, x):
        self.window.append(marcel.util.unwrap_op_output(x))
        if len(self.window) == self.op.n:
            self.flush_window()

    def flush(self):
        if len(self.window) > 0:
            padding = None
            while len(self.window) < self.op.n:
                self.window.append(padding)
            self.flush_window()
        self.op.propagate_flush()

