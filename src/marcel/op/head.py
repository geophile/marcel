import marcel.core


SUMMARY = '''
Output the leading items of the input stream, and discard the others.  
'''


DETAILS = '''
The first {n} items received from the input stream will be written to the
output stream. All other input items will be discarded. 
'''


def head():
    return Head()


class HeadArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('head', env, None, SUMMARY, DETAILS)
        self.add_argument('n',
                          type=super().constrained_type(marcel.core.ArgParser.check_non_negative,
                                                        'must be non-negative'),
                          help='The number of input items to keep.')


class Head(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.n = None
        self.received = 0

    def __repr__(self):
        return f'head({self.n})'

    # BaseOp
    
    def doc(self):
        return __doc__

    def setup_1(self):
        pass

    def receive(self, x):
        self.received += 1
        if self.n >= self.received:
            self.send(x)
