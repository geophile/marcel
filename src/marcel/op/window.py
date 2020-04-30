import marcel.core
import marcel.exception


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


def window():
    return Window()


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
                                type=super().constrained_type(marcel.core.ArgParser.check_non_negative,
                                                              'must be non-negative'),
                                help='Specifies the size of overlapping windows.')
        fixed_size.add_argument('-d', '--disjoint',
                                type=super().constrained_type(marcel.core.ArgParser.check_non_negative,
                                                              'must be non-negative'),
                                help='Specifies the size of disjoint windows.')


class Window(marcel.core.Op):

    def __init__(self):
        super().__init__()
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
            buffer.append(self.predicate.source)
        buffer.append(')')
        return ''.join(buffer)

    # BaseOp
    
    def doc(self):
        return __doc__

    def setup_1(self):
        # Exactly one of predicate, overlap, disjoint should be set. Not sure that argparse is up to that.
        count = 1 if self.predicate is not None else 0
        count += 1 if self.overlap is not None else 0
        count += 1 if self.disjoint is not None else 0
        if count != 1:
            raise marcel.exception.KillCommandException('Incorrect arguments given for window.')
        if self.predicate:
            self.window_generator = PredicateWindow(self)
            self.predicate.set_op(self)
        elif self.overlap:
            self.window_generator = OverlapWindow(self)
            self.n = self.overlap
        else:  # disjoint
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

