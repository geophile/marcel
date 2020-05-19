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

import marcel.core
import marcel.exception
import marcel.functionwrapper


SUMMARY = '''
Groups of consecutive input tuples are combined into a single tuple, which is written to
the output stream. 
'''


DETAILS = '''
Groups of consecutive input tuples are combined and written
to the output stream. The objects are grouped using one of two
mechanisms.

{b:Predicate-based:}

A new group is started on the first input object, and for any
subsequent object for which {r:predicate} returns true. For example, if
the input stream contains the integers {n:1, 2, 3, ...}, then:
{p,wrap=F}
    window (x: x % 3 == 2)

yields as output:
{p,wrap=F}
    ((1,),)
    ((2,), (3,), (4,))
    ((5,), (6,), (7,))
    ((8,), (9,), (10,))
    ...

I.e., a new tuple is started for each integer n, (after the first integer) such that n % 3 = 2.

{b:Fixed-size}:

Groups have a fixed number of objects. The {r:-o} and {r:-d} flags
specify {r:N}, the number of objects in the groups.  {r:-o}
specifies {i:overlapping} windows, in which each input object begins a
new list containing {r:N} items. Groups may be padded with
{r:None} values to ensure that the group's size is {r:N}.

{b:Example:}
 
For input {n:0, 1, ..., 9}, {r:window -o 3} yields these
tuples:
{p,wrap=F}
    ((0,), (1,), (2,))
    ((1,), (2,), (3,))
    ((2,), (3,), (4,))
    ((3,), (4,), (5,))
    ((4,), (5,), (6,))
    ((5,), (6,), (7,))
    ((6,), (7,), (8,))
    ((7,), (8,), (9,))
    ((8,), (9,), (None,))
    ((9,), (None,), (None,))

{r:-d} specifies {i:disjoint} windows, in which each input object
appears in only one group. A new group is started every {r:N}
objects. The last window may be padded with (None,) to ensure that it
has {r:N} elements.

{b:Example:}

For input {n:0, 1, ..., 9}, {r:window -d 3} yields these
tuples:
{p,wrap=F}
    ((0,), (1,), (2,))
    ((3,), (4,), (5,))
    ((6,), (7,), (8,))
    ((9,), (None,), (None,))
'''


def window(env, predicate=None, overlap=False, disjoint=None):
    op = Window(env)
    op.predicate = (None 
                    if predicate is None else
                    marcel.functionwrapper.FunctionWrapper(function=predicate))
    op.overlap = overlap
    op.disjoint = disjoint
    return op


class WindowArgsParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('window',
                         env,
                         ['-o', '--overlap', '-d', '--disjoint'],
                         SUMMARY,
                         DETAILS)
        self.add_argument('predicate',
                          nargs='?',
                          type=super().constrained_type(self.check_function, 'not a valid function'),
                          help='Start a new window on tuples for which predicate evaultes to True')
        fixed_size = self.add_mutually_exclusive_group()
        fixed_size.add_argument('-o', '--overlap',
                                type=int,
                                help='Specifies the size of overlapping windows.')
        fixed_size.add_argument('-d', '--disjoint',
                                type=int,
                                help='Specifies the size of disjoint windows.')


class Window(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.predicate = None
        self.overlap = None
        self.disjoint = None
        self.window_generator = None
        self.n = None

    def __repr__(self):
        buffer = ['window(']
        if self.overlap:
            buffer.append('overlap=')
            buffer.append(self.overlap)
        if self.disjoint:
            buffer.append('disjoint=')
            buffer.append(self.disjoint)
        if self.predicate:
            buffer.append('predicate=')
            buffer.append(self.predicate.source())
        buffer.append(')')
        return ''.join(buffer)

    # BaseOp

    def setup_1(self):
        # argparse seems to default args in mutually exclusive group to False instead of None
        if self.overlap == False:
            self.overlap = None    
        if self.disjoint == False:
            self.disjoint = None    
        # Exactly one of predicate, overlap, disjoint must be set.
        count = 1 if self.predicate is not None else 0
        count += 1 if self.overlap is not None else 0
        count += 1 if self.disjoint is not None else 0
        super().check_arg(count == 1,
                          None,
                          'Exactly one argument of window: predicate, overlap, or disjoint, must be specified.')
        if self.predicate:
            try:
                self.predicate.check_validity()
            except marcel.exception.KillCommandException:
                super().check_arg(False, 'predicate', 'Function either missing or invalid.')
            self.window_generator = PredicateWindow(self)
            self.predicate.set_op(self)
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

    def receive(self, x):
        self.window_generator.receive(x)

    def receive_complete(self):
        self.window_generator.receive_complete()
        self.send_complete()


class WindowBase:

    def __init__(self, op):
        self.op = op
        self.window = []

    def receive(self, x):
        assert False

    def receive_complete(self):
        assert False

    def flush(self):
        if len(self.window) > 0:
            self.op.send(self.window)
            self.window = []


class PredicateWindow(WindowBase):

    def __init__(self, op):
        super().__init__(op)

    def receive(self, x):
        if self.op.predicate(*x):
            self.flush()
        self.window.append(x)

    def receive_complete(self):
        self.flush()


class OverlapWindow(WindowBase):

    def __init__(self, op):
        super().__init__(op)

    def receive(self, x):
        if len(self.window) == self.op.n:
            self.window = self.window[1:]
        self.window.append(x)
        if len(self.window) == self.op.n:
            self.op.send(self.window)

    def receive_complete(self):
        padding = (None,)
        if len(self.window) < self.op.n:
            while len(self.window) < self.op.n:
                self.window.append(padding)
            self.op.send(self.window)
        for i in range(self.op.n - 1):
            self.window = self.window[1:]
            self.window.append(padding)
            self.op.send(self.window)


class DisjointWindow(WindowBase):

    def __init__(self, op):
        super().__init__(op)

    def receive(self, x):
        self.window.append(x)
        if len(self.window) == self.op.n:
            self.flush()

    def receive_complete(self):
        if len(self.window) > 0:
            padding = (None,)
            while len(self.window) < self.op.n:
                self.window.append(padding)
            self.flush()

