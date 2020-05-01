import marcel.core


SUMMARY = '''
Generates a stream of {r:count} integers, starting at {r:start}.
'''


DETAILS = '''
The first integer in the stream is {r:start}. The number of integers in the stream is {r:count},
although if {r:count} is 0, then the stream does not terminate. If {r:pad} is specified, 
then each integer is converted to a string and left-padded with zeros. Padding is not 
permitted if the stream does not terminate, or if {r:start} is negative.
'''


def gen(count=0, start=0, pad=None):
    op = Gen()
    op.count = count
    op.start = start
    op.pad = pad
    return op


class GenArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('gen', env, ['-p', '--pad'], SUMMARY, DETAILS)
        self.add_argument('-p', '--pad',
                          type=int,
                          help='Left-pad with zeros to PAD characters')
        self.add_argument('count',
                          nargs='?',
                          default='0',
                          type=super().constrained_type(marcel.core.ArgParser.check_non_negative,
                                                        'must be non-negative'),
                          help='''The number of integers to generate. Must be non-negative.
                          Default value is 0. 
                          If 0, then the sequence does not terminate''')
        self.add_argument('start',
                          nargs='?',
                          default='0',
                          type=int,
                          help='The first integer in the stream. Default value is 0.')


class Gen(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.pad = None
        self.count = None
        self.start = None
        self.format = None

    def __repr__(self):
        return f'gen(count={self.count}, start={self.start}, pad={self.pad})'

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup_1(self):
        if self.pad is not None:
            if self.count == 0:
                raise marcel.exception.KillCommandException('Padding incompatible with unbounded output')
            elif self.start < 0:
                raise marcel.exception.KillCommandException('Padding incompatible with START < 0')
            else:
                max_length = len(str(self.start + self.count - 1))
                if max_length > self.pad:
                    raise marcel.exception.KillCommandException('Padding too small.')
                else:
                    self.format = '{:>0' + str(self.pad) + '}'

    def receive(self, _):
        if self.count is None or self.count == 0:
            x = self.start
            while True:
                self.send(self.apply_padding(x))
                x += 1
        else:
            for x in range(self.start, self.start + self.count):
                self.send(self.apply_padding(x))

    # Op

    def must_be_first_in_pipeline(self):
        return True

    # For use by this class

    def apply_padding(self, x):
        return (self.format.format(x)) if self.format else x
