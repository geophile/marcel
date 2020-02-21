"""C{red [-i|--incremental] [FUNCTION ...]}

Reduces input elements by repeatedly applying binary functions such as +, min, max.

-i|--incremental           Instead of producing one row of output for each reduction, write partial
                           results to output for each input row.

FUNCTION                   A binary function used to combine values from rows.

Each C{FUNCTION} takes two inputs and produces one output.

B{Basic usage:}

For example, given a sequence of inputs such as C{(1,), (2,), (3,)}, C{red} can be used to find the sum::

    ... | red +

yields C{(6,)}. For input elements with more than a single value, multiple functions can be provided.
For example, to find the sum of 0 ... 9, the sum of their squares, and the sum of their cubes::

    osh gen 10 | map (x: (x, x**2, x**3)) ^ red + + +

which yields the output C{(45, 285, 2025)}.

B{Grouping:}

Functions can be computed within groups of input rows, identifying the group-defining
values using C{.} instead of a function. For example, suppose the input sequence is::

    (1, 5, 10, 100)
    (1, 6, 10, 200)
    (1, 4, 11, 100)
    (1, 3, 11, 200)
    (2, 8, 20, 100)
    (2, 9, 20, 200)
    (2, 10, 20, 300)
    (3, 5, 30, 100)

If this sequence is piped to this invocation of C{red}::

    red . + . +

then groups are defined using the first and third values, C{(1, 10), (1, 11), (2, 20), (3, 30)}.
The output would be::

    (1, 11, 10, 300)
    (1, 7, 11, 300)
    (2, 17, 20, 300)
    (3, 5, 30, 100)

B{Incremental mode:}

If the C{-i} flag is specified, then one output element is generated for each input element;
an output element contains the current accumulated values. The accumulator appears
in the output element after the inputs. For example, if the input stream contains C{(1,), (2,), (3,)},
then the running total can be computed as follows::

    ... | red -i + | ...

The output stream would be C{(1, 1), (2, 3), (3, 6)}. In the last output object, C{6} is the sum
of the current input (C{3}) and all preceding inputs (C{1, 2}).

The C{-i} flag can also be used with grouping. For example, if the input el
ements are
C{('a', 1), ('a', 2), ('b', 3), ('b', 4)}, then the running totals, grouped by the string values would
be computed as follows::

    ... | red -i . +

The output stream would be C{('a', 1, 1), ('a', 2, 3), ('b', 3, 3), ('b', 4, 7)}.

"""

import argparse

import marcel.core


def red():
    return Red()


class RedArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('red')
        self.add_argument('-i', '--incremental',
                          action='store_true')
        self.add_argument('function',
                          nargs=argparse.REMAINDER,
                          type=super().constrained_type(marcel.core.ArgParser.check_function,
                                                        'not a valid function'))


class Red(marcel.core.Op):

    argparser = RedArgParser()

    def __init__(self):
        super().__init__()
        self.incremental = None
        self.function = None
        self.reducer = None

    def __repr__(self):
        return ('red(incremental = %s, function = %s)' %
                (self.incremental, [(f.source if f else None)
                                    for f in self.function]))

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup_1(self):
        grouping_positions = []
        data_positions = []
        for i in range(len(self.function)):
            function = self.function[i]
            function.set_op(self)
            if Red.is_grouping(function.source):
                grouping_positions.append(i)
                self.function[i] = None
            else:
                data_positions.append(i)
        if len(grouping_positions) == 0:
            self.reducer = NonGroupingReducer(self)
        else:
            self.reducer = GroupingReducer(self, grouping_positions, data_positions)

    def receive(self, x):
        self.reducer.receive(x)

    def receive_complete(self):
        self.reducer.receive_complete()

    # Op

    def arg_parser(self):
        return Red.argparser

    # For use by this class

    @staticmethod
    def is_grouping(function):
        return function == '.'


class Reducer:

    def __init__(self, op):
        self.function = op.function
        self.op = op
        self.n = len(self.function)

    def receive(self, x):
        assert False

    def receive_complete(self):
        assert False


class NonGroupingReducer(Reducer):

    def __init__(self, op):
        super().__init__(op)
        self.accumulator = None

    def receive(self, x):
        accumulator = self.accumulator
        if accumulator is None:
            accumulator = list(x)
            self.accumulator = accumulator
        else:
            function = self.function
            for i in range(self.n):
                accumulator[i] = function[i](accumulator[i], x[i])
        if self.op.incremental:
            self.op.send(x + tuple(accumulator))

    def receive_complete(self):
        if not self.op.incremental:
            self.op.send(self.accumulator)
        self.op.send_complete()


class GroupingReducer(Reducer):

    def __init__(self, op, grouping_positions, data_positions):
        super().__init__(op)
        self.function = op.function
        self.grouping_positions = grouping_positions
        self.data_positions = data_positions
        self.accumulators = {}  # group -> accumulator

    def receive(self, x):
        group = tuple(self.group(x))
        accumulator = self.accumulators.get(group, None)
        if accumulator is None:
            accumulator = list(x)
            self.accumulators[group] = accumulator
        else:
            for i in range(self.n):
                reducer = self.function[i]
                if reducer:
                    accumulator[i] = reducer(accumulator[i], x[i])
                # else: x[i] is part of the group
        if self.op.incremental:
            self.op.send(x + tuple(self.data(accumulator)))

    def receive_complete(self):
        if not self.op.incremental:
            for _, data in self.accumulators.items():
                self.op.send(data)
        self.op.send_complete()

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
