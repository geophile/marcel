"""C{gen [-p|--pad PAD] [COUNT [START]]}

Generate a sequence of C{COUNT} integers, starting at C{START}. C{COUNT} must be non-negative.
If C{START} is not specified, then the sequence starts at 0. If C{COUNT} is 0 or is not specified,
then the sequence does not terminate.

-p | --pad PAD             The generated integers are converted to strings and left-padded with zeros
                           so that each string contains C{PAD} characters. The number of digits in each
                           member of the generated sequence must not exceed C{PAD}. This option queries
                           C{START} >= 0.
"""

import osh.core


def gen():
    return Gen()


class GenArgParser(osh.core.OshArgParser):

    def __init__(self):
        super().__init__('gen')
        self.add_argument('-p', '--pad',
                          type=int)
        self.add_argument('count',
                          nargs='?',
                          default='0',
                          type=super().constrained_type(osh.core.OshArgParser.check_non_negative,
                                                        'must be non-negative'))
        self.add_argument('start',
                          nargs='?',
                          default='0',
                          type=int)


class Gen(osh.core.Op):

    argparser = GenArgParser()

    def __init__(self):
        super().__init__()
        self.pad = None
        self.count = None
        self.start = None
        self.format = None

    def __repr__(self):
        return 'gen(count=%s, start=%s, pad=%s)' % (self.count, self.start, self.pad)

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup(self):
        if self.pad is not None:
            if self.count == 0:
                Gen.argparser.error('Padding incompatible with unbounded output')
            elif self.start < 0:
                Gen.argparser.error('Padding incompatible with START < 0')
            else:
                max_length = len(str(self.start + self.count - 1))
                if max_length > self.pad:
                    Gen.argparser.error('Padding too small.')
                else:
                    self.format = '%%0%sd' % self.pad

    def execute(self):
        if self.count is None or self.count == 0:
            x = self.start
            while True:
                self.send(self.apply_padding(x))
                x += 1
        else:
            for x in range(self.start, self.start + self.count):
                self.send(self.apply_padding(x))

    # Op

    def arg_parser(self):
        return Gen.argparser

    # For use by this class

    def apply_padding(self, x):
        return (self.format % x) if self.format else x
