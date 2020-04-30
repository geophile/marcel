import marcel.core
import marcel.util


SUMMARY = '''
Flatten input tuples (or parts of them) and write the flattened result to the output stream.
'''


DETAILS = '''
If {r:position} is omitted, then each element of an input tuple is generated as a separate
1-tuple in the output stream. (If the input has one element, then the output matches the input.)
If {r:position} is provided, it must be non-negative. If {r:position} exceeds the length of an
input sequence, then nothing is expanded (the input sequence is sent as output).

{b:Example}: If the input contains these sequences:
{p,wrap=F}
    (100, 101)
    (200, 201)

then {r:expand} generates this output:
{p,wrap=F}
    100
    101
    200
    201

If {r:position} is specified, then presumably each input tuple has a sequence (or iterator) 
at the indicated position.
An output tuple is generated for each item in that embedded sequence, replacing the embedded
sequence by one of its contained items.

The types that can be expanded are sequences ({r:list}, {r:tuple}, {r:str}), {r:generator}s, 
{r:iterator}s and Files.
Expansion of a {r:File} yields each line of the named file.

{b:Example}: If the input contains these sequences:
{p,wrap=F}
    ('a', [1, 2, 3], 'x')
    ('b', [4, 5], 'y')
    ('c', [], 'z')

then {r:expand 1} generates this output:
{p,wrap=F}
    ('a', 1, 'x')
    ('a', 2, 'x')
    ('a', 3, 'x')
    ('b', 4, 'y')
    ('b', 5, 'y')

Note that an empty nested sequence (as in the last input tuple) results in no output.
'''


def expand():
    return Expand()


class ExpandArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('expand', env, None, SUMMARY, DETAILS)
        self.add_argument('position',
                          nargs='?',
                          type=super().constrained_type(marcel.core.ArgParser.check_non_negative,
                                                        'must be non-negative'),
                          help='Position of the tuple to be expanded')


class Expand(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.position = None
        self.expander = None

    def __repr__(self):
        return 'expand()' if self.position is None else f'expand({self.position})'

    # BaseOp

    def doc(self):
        return __doc__

    def setup_1(self):
        self.expander = SequenceExpander(self) if self.position is None else ComponentExpander(self)

    def receive(self, x):
        self.expander.receive(x)


class Expander:

    def __init__(self, op):
        self.op = op

    def receive(self, sequence):
        assert False

    @staticmethod
    def expand(x):
        if marcel.util.is_sequence(x):
            if len(x) != 1:
                return x
            only = x[0]
            # TODO: Generators
            if marcel.util.is_sequence(only):
                return only
            elif marcel.util.is_file(only):
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
        return f'Object of type {type(self.not_expandable)} cannot be expanded: {self.not_expandable}'
