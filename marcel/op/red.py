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
import marcel.function
import marcel.reduction

HELP = '''
{L,wrap=F}red [-i|--incremental] FUNCTION ...

{L,indent=4:28}{r:-i}, {r:--incremental}       Output a tuple for each step of the reduction. I.e., there will be one
output tuple for each input tuple, with the reductions showing the result of the reduction up to and including
the most recent input.

{L,indent=4:28}{r:FUNCTION}                A reduction function.


Reduces tuples from the input stream by repeatedly applying binary functions, such as {r:+}, {r:min}, {r:max}.

Each {r:FUNCTION} takes two inputs and produces one output.

{b:Basic usage}

Given a sequence of inputs such as {n:(1,), (2,), (3,)}, {r:red} can be used to find the sum:
{p,wrap=F}
    ... | red +

yields {r:(6,)}. For input elements with more than a single value, multiple functions can be provided.
For example, to find the sum of 0 ... 9, the sum of their squares, and the sum of their cubes:
{p,wrap=F}
    gen 10 | map (x: (x, x**2, x**3)) | red + + +

which yields the output {n:(45, 285, 2025)}.

The {r:count} function can be used to count the number of input tuples, e.g.
{p,wrap=F}
    gen 10 | red count
    
yields the output {n:10}.

{b:Grouping}

Reduction can be applied to groups of input rows, identifying the group-defining
values using {r:.} instead of a function. For example, suppose the input sequence is:
{p,wrap=F}
    (1, 5, 10, 100)
    (1, 6, 10, 200)
    (1, 4, 11, 100)
    (1, 3, 11, 200)
    (2, 8, 20, 100)
    (2, 9, 20, 200)
    (2, 10, 20, 300)
    (3, 5, 30, 100)

If this sequence is piped to this invocation of {r:red}:
{p,wrap=F}
    red . + . +

then groups are defined using the first and third values, {n:(1, 10), (1, 11), (2, 20), (3, 30)}.
The output would be:
{p,wrap=F}
    (1, 11, 10, 300)
    (1, 7, 11, 300)
    (2, 17, 20, 300)
    (3, 5, 30, 100)

{b:Incremental mode:}

If the {r:-i} flag is specified, then one output tuple is generated for each input tuple;
an output element contains the current accumulated values. The accumulator appears
in the output element after the inputs. For example, if the input stream contains {n:(1,), (2,), (3,)},
then the running total can be computed as follows:
{p,wrap=F}
    ... | red -i + | ...

The output stream would be {n:(1, 1), (2, 3), (3, 6)}. In the last output tuple, {n:6} is the sum
of the current input ({n:3}) and all preceding inputs ({n:1, 2}).

The {r:-i} flag can also be used with grouping. For example, if the input 
tuples are
{n:('a', 1), ('a', 2), ('b', 3), ('b', 4)}, then the running totals, grouped by the string values would
be computed as follows:
{p,wrap=F}
    ... | red -i . +

The output stream would be {n:('a', 1, 1), ('a', 2, 3), ('b', 3, 3), ('b', 4, 7)}.

{b:Errors}

If {n:n} reduction functions are specified, then input tuples are expected to have at least {n:n}
elements. Each shorter tuples will cause an {n:Error} to be output. For longer tuples, elements after
the first {n:n} will be ignored. 
'''


def red(env, *functions, incremental=False):
    args = ['--incremental'] if incremental else []
    args.extend([marcel.reduction.r_group if f is None else f for f in functions])
    return Red(env), args


class RedArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('red', env)
        self.add_flag_no_value('incremental', '-i', '--incremental')
        self.add_anon_list('functions', convert=self.function)
        self.validate()


class Red(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.incremental = None
        self.functions = None
        self.reducer = None

    def __repr__(self):
        sources = [None if f is None else f.snippet() for f in self.functions]
        flags = 'incremental, ' if self.incremental else ''
        return f'red({flags}functions={sources})'

    # AbstractOp

    def setup(self):
        grouping_positions = []
        data_positions = []
        for i in range(len(self.functions)):
            function = self.functions[i]
            if function.is_grouping():
                grouping_positions.append(i)
                self.functions[i] = None
            else:
                data_positions.append(i)
        if len(grouping_positions) == 0:
            self.reducer = NonGroupingReducer(self)
        else:
            self.reducer = GroupingReducer(self, grouping_positions, data_positions)

    def set_env(self, env):
        super().set_env(env)
        for function in self.functions:
            if isinstance(function, marcel.function.Function):
                function.set_globals(env.vars())

    # Op

    def receive(self, x):
        self.reducer.receive(x)

    def receive_complete(self):
        self.reducer.receive_complete()


class Reducer:

    def __init__(self, op):
        self.op = op
        self.n = len(self.op.functions)

    def receive(self, x):
        assert False

    def receive_complete(self):
        assert False


class NonGroupingReducer(Reducer):

    def __init__(self, op):
        super().__init__(op)
        self.accumulator = [None] * self.n

    def receive(self, x):
        op = self.op
        if len(x) < self.n:
            op.fatal_error(x, 'Input too short.')
        accumulator = self.accumulator
        functions = op.functions
        for i in range(self.n):
            accumulator[i] = op.call(functions[i], accumulator[i], x[i])
        if op.incremental:
            op.send(x + tuple(accumulator))

    def receive_complete(self):
        op = self.op
        if not op.incremental and self.accumulator is not None:
            op.send(tuple(self.accumulator))
            self.accumulator = None
        op.send_complete()


class GroupingReducer(Reducer):

    def __init__(self, op, grouping_positions, data_positions):
        super().__init__(op)
        self.grouping_positions = grouping_positions
        self.data_positions = data_positions
        self.accumulators = {}  # group -> accumulator

    def receive(self, x):
        op = self.op
        if len(x) < self.n:
            op.fatal_error(x, 'Input too short.')
        group = tuple(self.group(x))
        accumulator = self.accumulators.get(group, None)
        if accumulator is None:
            accumulator = [None] * self.n
            self.accumulators[group] = accumulator
        for i in range(self.n):
            reducer = op.functions[i]
            accumulator[i] = op.call(reducer, accumulator[i], x[i]) if reducer else x[i]
        if op.incremental:
            op.send(x + tuple(self.data(accumulator)))

    def receive_complete(self):
        op = self.op
        if not op.incremental and self.accumulators is not None:
            for _, data in self.accumulators.items():
                op.send(tuple(data))
                self.accumulators = None
        op.send_complete()

    def group(self, x):
        group = []
        for p in self.grouping_positions:
            group.append(x[p])
        return group

    def data(self, x):
        data = []
        for p in self.data_positions:
            data.append(x[p])
        return data
