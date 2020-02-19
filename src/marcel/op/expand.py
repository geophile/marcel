"""C{expand [POSITION]}

If C{POSITION} is omitted, then each element of an input sequence is generated as a separate
1-tuple in the output stream. (If the input has one element, then the output matches the input.)
If C{POSITION} is provided, it must be non-negative. If C{POSITION} exceeds the length of an
input sequence, then nothing is expanded (the input sequence is sent as output).

B{Example}: If the input contains these sequences::

    (100, 101)
    (200, 201)

then C{expand} generates this output::

    (100,)
    (101,)
    (200,)
    (201,)

If C{POSITION} is specified, then presumably each input element has a sequence at the indicated position.
An output element is generated for each element of that embedded sequence, replacing the embedded
sequence by one of its contained elements.

The types that can be expanded are sequences (C{list}, C{tuple}, C{str}), C{generator}, and C{osh.file.File}.
Expansion of a C{osh.file.File} yields each line of the named file.

B{Example}: If the input contains these sequences::

    ('a', [1, 2, 3], 'x')
    ('b', [4, 5], 'y')
    ('c', [], 'z')

then C{expand 1} generates this output::

    ('a', 1, 'x')
    ('a', 2, 'x')
    ('a', 3, 'x')
    ('b', 4, 'y')
    ('b', 5, 'y')

Note that an empty nested sequence results in no output, (as for
C{('c', [], 'z')}.)
"""

import marcel.core
from marcel.util import *


def expand():
    return Expand()


class ExpandArgParser(marcel.core.OshArgParser):

    def __init__(self):
        super().__init__('expand')
        self.add_argument('position',
                          nargs='?',
                          type=super().constrained_type(marcel.core.OshArgParser.check_non_negative,
                                                        'must be non-negative'))


class Expand(marcel.core.Op):
    argparser = ExpandArgParser()

    def __init__(self):
        super().__init__()
        self.position = None
        self.expander = None

    def __repr__(self):
        return 'expand()' if self.position is None else 'expand(position=%s)' % self.position

    # BaseOp interface

    def doc(self):
        return __doc__

    def setup_1(self):
        self.expander = SequenceExpander(self) if self.position is None else ComponentExpander(self)

    def receive(self, x):
        self.expander.receive(x)

    # Op

    def arg_parser(self):
        return Expand.argparser


class Expander:

    def __init__(self, op):
        self.op = op

    def receive(self, sequence):
        assert False

    @staticmethod
    def expand(x):
        if is_sequence(x):
            if len(x) != 1:
                return x
            only = x[0]
            # TODO: Generators
            if is_sequence(only):
                return only
            elif is_file(only):
                lines = []
                with open(only.path, 'r') as file:
                    for line in file.readlines():
                        # Remove EOL whitespace
                        if line.endswith('\r\n') or line.endswith('\n\r'):
                            line = line[:-2]
                        elif line.endswith('\r') or line.endswith('\n'):
                            line = line[:-1]
                        lines.append(line)
                return lines
            else:
                return x
        else:
            return [x]


class SequenceExpander(Expander):

    def __init__(self, op):
        super().__init__(op)

    def receive(self, sequence):
        for x in Expander.expand(sequence):
            self.op.send(x)


class ComponentExpander(Expander):

    def __init__(self, op):
        super().__init__(op)
        self.position = op.position

    def receive(self, sequence):
        if self.position >= len(sequence):
            self.op.send(sequence)
        else:
            assert self.position >= 0
            assert self.position < len(sequence)
            pre = sequence[:self.position]
            post = sequence[(self.position + 1):]
            send = self.op.send
            for x in Expander.expand([sequence[self.position]]):
                send(pre + (x,) + post)


class NotExpandableException(Exception):
    not_expandable = None

    def __init__(self, not_expandable):
        self.not_expandable = not_expandable

    def __str__(self):
        return 'Object of type %s cannot be expanded: %s' % (type(self.not_expandable), self.not_expandable)
