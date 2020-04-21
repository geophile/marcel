import marcel.core


SUMMARY = '''
The input stream is sorted and written to the output stream.
'''


DETAILS = '''
If {key} is not specified, then input tuples are ordered according to Python rules.
Otherwise, ordering is based on the values computed by applying {key} to each input tuple.
'''


def sort():
    return Sort()


class SortArgParser(marcel.core.ArgParser):
    
    def __init__(self, global_state):
        super().__init__('sort', global_state, None, SUMMARY, DETAILS)
        self.add_argument('key',
                          nargs='?',
                          default=None,
                          type=super().constrained_type(self.check_function, 'not a valid function'),
                          help='Function to obtain the value used for ordering.')


class Sort(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.key = None
        self.contents = []

    def __repr__(self):
        return 'sort'

    # BaseOp
    
    def doc(self):
        return __doc__

    def setup_1(self):
        if self.key:
            self.key.set_op(self)

    def receive(self, x):
        self.contents.append(x)
    
    def receive_complete(self):
        if self.key:
            self.contents.sort(key=lambda t: self.key(*t))
        else:
            self.contents.sort()
        for x in self.contents:
            self.send(x)
        self.send_complete()
