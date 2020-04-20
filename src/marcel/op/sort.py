"""C{sort [KEY]}

Input objects are sorted before being written to output. Ordering is based on the use of comparison operators
for type input objects, except if KEY (a function) is provided. In that case, the comparison operators are applied
to the values obtained by applying the KEY function to the input objects.

KEY                        Obtains the sort key. If omitted, the object itself is used as the sort key.
"""

import marcel.core


def sort():
    return Sort()


class SortArgParser(marcel.core.ArgParser):
    
    def __init__(self, global_state):
        super().__init__('sort', global_state)
        self.add_argument('key',
                          nargs='?',
                          default=None,
                          type=super().constrained_type(self.check_function, 'not a valid function'))


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
