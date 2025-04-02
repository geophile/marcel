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
evaluates to {n:True}.

Groups of consecutive input tuples are combined into a single tuple, which is written to
the output stream. 

The objects are grouped using one of two
mechanisms.

{b:Predicate-based:}

A new group is started on the first input object, and for any
subsequent object for which {r:PREDICATE} returns true. For example, if
the input stream contains the integers {n:1, 2, 3, ...}, then:
{p,wrap=F}
    window (f: f % 3 == 2)

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


def window(predicate=None, overlap=None, disjoint=None):
    args = []
    if overlap is not None:
        args.extend(['--overlap', overlap])
    if disjoint is not None:
        args.extend(['--disjoint', disjoint])
    if predicate:
        args.append(predicate)
    return Window(), args


class WindowArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('window', env)
        self.add_flag_one_value('overlap', '-o', '--overlap', convert=self.str_to_int, target='overlap_arg')
        self.add_flag_one_value('disjoint', '-d', '--disjoint', convert=self.str_to_int, target='disjoint_arg')
        self.add_anon('predicate', convert=self.function, default=None)
        self.exactly_one('overlap', 'disjoint', 'predicate')
        self.validate()


class Window(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.predicate = None
        self.overlap_arg = None
        self.overlap = None
        self.disjoint_arg = None
        self.disjoint = None
        self.window_generator = None
        self.n = None

    def __repr__(self):
        options = []
        if self.overlap:
            options.append(f'overlap={self.overlap}')
        if self.disjoint:
            options.append(f'disjoint={self.disjoint}')
        if self.predicate:
            options.append(f'predicate={self.predicate.source()}')
        return f'window({", ".join(options)})'

    # AbstractOp

    def setup(self, env):
        self.overlap = self.eval_function(env, 'overlap_arg', int)
        self.disjoint = self.eval_function(env, 'disjoint_arg', int)
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
        if self.predicate:
            env.set_function_globals(self.predicate)

    # Op

    def receive(self, env, x):
        self.window_generator.receive(env, x)

    def flush(self, env):
        if self.window_generator is not None:
            self.window_generator.flush(env)


class WindowBase:

    def __init__(self, op):
        self.op = op
        self.window = []

    def receive(self, env, x):
        assert False

    def flush(self, env):
        assert False

    def send_window(self, env):
        self.op.send(env, tuple(self.window))

    def flush_window(self, env):
        if len(self.window) > 0:
            self.send_window(env)
            self.window = []


class PredicateWindow(WindowBase):

    def __init__(self, op):
        super().__init__(op)

    def receive(self, env, x):
        if self.op.call(env, self.op.predicate, *x):
            self.flush_window(env)
        self.window.append(marcel.util.unwrap_op_output(x))

    def flush(self, env):
        self.flush_window(env)
        self.op.propagate_flush(env)


class OverlapWindow(WindowBase):

    def __init__(self, op):
        super().__init__(op)

    def receive(self, env, x):
        if len(self.window) == self.op.n:
            self.window = self.window[1:]
        self.window.append(marcel.util.unwrap_op_output(x))
        if len(self.window) == self.op.n:
            self.send_window(env)

    def flush(self, env):
        if len(self.window) > 0:
            padding = None
            if len(self.window) < self.op.n:
                while len(self.window) < self.op.n:
                    self.window.append(padding)
                self.send_window(env)
            for i in range(self.op.n - 1):
                self.window = self.window[1:]
                self.window.append(padding)
                self.send_window(env)
            self.op.propagate_flush(env)


class DisjointWindow(WindowBase):

    def __init__(self, op):
        super().__init__(op)

    def receive(self, env, x):
        self.window.append(marcel.util.unwrap_op_output(x))
        if len(self.window) == self.op.n:
            self.flush_window(env)

    def flush(self, env):
        if len(self.window) > 0:
            padding = None
            while len(self.window) < self.op.n:
                self.window.append(padding)
            self.flush_window(env)
        self.op.propagate_flush(env)

