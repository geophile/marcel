# osh1 does a clone of a pipeline, being careful to replace functions by references before the copy, and then fix up
# the copy afterward. Is this really necessary?

import io
import pickle


class AbstractOp:

    def __init__(self):
        """
        Initialize the instance

        Args:
            self: (todo): write your description
        """
        self.base = 111


class Op(AbstractOp):

    def __init__(self, name, f):
        """
        Initialize the next instance.

        Args:
            self: (todo): write your description
            name: (str): write your description
            f: (int): write your description
        """
        super().__init__()
        self.name = name
        self.f = f
        self.next = None

    def __repr__(self):
        """
        Generate a human - friendly representation.

        Args:
            self: (todo): write your description
        """
        return 'Op(#{}, {}, {})'.format(hash(self), self.name, self.base)

    def __getstate__(self):
        """
        Get the state of the object.

        Args:
            self: (todo): write your description
        """
        return self.__dict__

    def __setstate__(self, state):
        """
        Sets the state of a given state.

        Args:
            self: (todo): write your description
            state: (dict): write your description
        """
        self.__dict__.update(state)

    def connect(self, next):
        """
        Connect to the next node.

        Args:
            self: (todo): write your description
            next: (str): write your description
        """
        self.next = next

    def run(self):
        """
        Runs the function.

        Args:
            self: (todo): write your description
        """
        return self.f(self)


def f(op):
    """
    Return a string representation of an op.

    Args:
        op: (todo): write your description
    """
    return 'In f({})'.format(op.name)


def g(op):
    """
    Return a string representation of an op.

    Args:
        op: (todo): write your description
    """
    return 'In g({})'.format(op.name)


def traverse(label, op):
    """
    Traverse the op.

    Args:
        label: (todo): write your description
        op: (todo): write your description
    """
    print(label)
    while op:
        print('    {}: {}'.format(op, op.run()))
        op = op.next


def clone(x):
    """
    Clone object.

    Args:
        x: (todo): write your description
    """
    buffer = io.BytesIO()
    pickler = pickle.Pickler(buffer)
    pickler.dump(x)
    buffer.seek(0)
    unpickler = pickle.Unpickler(buffer)
    return unpickler.load()


a = Op('a', f)
b = Op('b', g)
a.connect(b)
traverse('original', a)

acopy = clone(a)
traverse('copy', acopy)