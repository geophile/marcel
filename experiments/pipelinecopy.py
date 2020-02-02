# osh1 does a clone of a pipeline, being careful to replace functions by references before the copy, and then fix up
# the copy afterward. Is this really necessary?

import io
import pickle


class Op:

    def __init__(self, name, f):
        self.name = name
        self.f = f
        self.next = None

    def __repr__(self):
        return 'Op(#%s, %s)' % (hash(self), self.name)

    def connect(self, next):
        self.next = next

    def run(self):
        return self.f(self)


def f(op):
    return 'In f(%s)' % op.name


def g(op):
    return 'In g(%s)' % op.name


def traverse(label, op):
    print(label)
    while op:
        print('    %s: %s' % (op, op.run()))
        op = op.next


def clone(x):
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