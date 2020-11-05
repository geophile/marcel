from time import *


class Op:

    def __init__(self, n, label):
        """
        Initialize the next label.

        Args:
            self: (todo): write your description
            n: (int): write your description
            label: (str): write your description
        """
        self.label = label
        self.n = n
        self.next_op = None
        self.prev_op = None

    def connect(self, next_op):
        """
        Connects to the next operation.

        Args:
            self: (todo): write your description
            next_op: (str): write your description
        """
        self.next_op = next_op
        next_op.prev_op = self

    def receive(self, x):
        """
        Receive the next n bytes.

        Args:
            self: (todo): write your description
            x: (todo): write your description
        """
        for i in range(self.n):
            output = self.output(i)
            self.next_op.receive(output if x is None else x + output)

    def pull(self):
        """
        Yield the next n elements from the stream.

        Args:
            self: (todo): write your description
        """
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
        """
        Return the output of the i { i }.

        Args:
            self: (todo): write your description
            i: (todo): write your description
        """
        return '{}{}'.format(self.label, i),


class Terminal(Op):

    def __init__(self):
        """
        Initialize the init

        Args:
            self: (todo): write your description
        """
        super().__init__(None, None)

    def receive(self, x):
        """
        Receive the callback function.

        Args:
            self: (todo): write your description
            x: (todo): write your description
        """
        pass

    def pull(self):
        """
        Pulls all the elements from the queue.

        Args:
            self: (todo): write your description
        """
        source = self.prev_op.pull()
        try:
            while True:
                str(next(source))
        except StopIteration:
            pass


def measure(label, function):
    """
    Print a function

    Args:
        label: (str): write your description
        function: (todo): write your description
    """
    start = time_ns()
    function()
    stop = time_ns()
    msec = (stop - start) / 1000000
    print('{}: {} msec'.format(label, msec))


def main():
    """
    Main function.

    Args:
    """
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
