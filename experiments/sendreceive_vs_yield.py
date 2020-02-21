from time import *


class Op:

    def __init__(self, n, label):
        self.label = label
        self.n = n
        self.next_op = None
        self.prev_op = None

    def connect(self, next_op):
        self.next_op = next_op
        next_op.prev_op = self

    def receive(self, x):
        for i in range(self.n):
            output = self.output(i)
            self.next_op.receive(output if x is None else x + output)

    def pull(self):
        prev_op = self.prev_op
        if prev_op:
            source = prev_op.pull()
            try:
                while True:
                    x = next(source)
                    for i in range(self.n):
                        yield x + self.output(i)
            except StopIteration:
                pass
        else:
            for i in range(self.n):
                yield self.output(i)

    def output(self, i):
        return '{}{}'.format(self.label, i),


class Terminal(Op):

    def __init__(self):
        super().__init__(None, None)

    def receive(self, x):
        pass

    def pull(self):
        source = self.prev_op.pull()
        try:
            while True:
                str(next(source))
        except StopIteration:
            pass


def measure(label, function):
    start = time_ns()
    function()
    stop = time_ns()
    msec = (stop - start) / 1000000
    print('{}: {} msec'.format(label, msec))


def main():
    a = Op(200, 'a')
    b = Op(200, 'b')
    c = Op(200, 'c')
    t = Terminal()
    a.connect(b)
    b.connect(c)
    c.connect(t)
    measure('send/receive', lambda: a.receive(None))
    measure('yield', lambda: t.pull())


main()
