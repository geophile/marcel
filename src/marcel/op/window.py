"""C{window PREDICATE
C{window -o|--overlap N}
C{window -d|--disjoint N}

PREDICATE                  Start a new group when PREDICATE, applied to the current input, evaluates to True
-o N                       Start a new group of size N on each input. Groups overlap.
-d N                       Start a new group of size N after every N inputs. Groups are disjoint.

Groups of consecutive input elements are formed into tuples which are
passed to the output stream. The objects are grouped using one of two
mechanisms.

1) A new group is started on the first input object, and for any
subsequent object for which C{PREDICATE} returns true. For example, if
the input stream contains the integers C{1, 2, 3, ...}, then::

    window (x: x % 3 == 2)

yields as output::

    ((1,),)
    ((2,), (3,), (4,))
    ((5,), (6,), (7,))
    ((8,), (9,), (10,))
    ...

I.e., a new tuple is started for each integer n, (after the first integer) such that n % 3 = 2.

2) Groups have a fixed number of objects. The C{-o} and C{-d} flags
specify C{N}, the number of objects in the groups.  C{-o}
specifies I{overlapping} windows, in which each input object begins a
new list containing C{N} items. Groups may be padded with
C{None} values to ensure that the group's size is C{N}.
    
B{Example}: For input C{0, 1, ..., 9}, C{window -o 3} yields these
tuples::
    
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

C{-d} specifies I{disjoint} windows, in which each input object
appears in only one group. A new group is started every C{N}
objects. The last window may be padded with (None,) to ensure that it
has C{N} elements.
    
B{Example}: For input C{0, 1, ..., 9}, C{window -d 3} yields these
tuples::
    
    ((0,), (1,), (2,))
    ((3,), (4,), (5,))
    ((6,), (7,), (8,))
    ((9,), (None,), (None,))
"""


def window():
    return Window()


class WindowArgsParser(marcel.osh.core.OshArgParser):

    def __init__(self):
        super().__init__('window')
        self.add_argument('predicate',
                          nargs='?',
                          type=super().constrained_type(marcel.osh.core.OshArgParser.check_function,
                                                        'not a valid function'))
        fixed_size = self.add_mutually_exclusive_group()
        fixed_size.add_argument('-o', '--overlap',
                                type=super().constrained_type(marcel.osh.core.OshArgParser.check_non_negative,
                                                              'must be non-negative'))
        fixed_size.add_argument('-d', '--disjoint',
                                type=super().constrained_type(marcel.osh.core.OshArgParser.check_non_negative,
                                                              'must be non-negative'))


class Window(marcel.osh.core.Op):

    argparser = WindowArgsParser()

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
            buffer.append('overlap=%s')
            buffer.append(self.overlap)
        if self.disjoint:
            buffer.append('disjoint=%s')
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
            raise marcel.osh.error.KillCommandException('Incorrect arguments given for window.')
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

    # Op

    def arg_parser(self):
        return Window.argparser


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

