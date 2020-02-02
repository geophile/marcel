import sys
import pwd
import grp
import collections.abc
import io
import pickle
import traceback


def username(uid):
    return pwd.getpwuid(uid).pw_name


def groupname(gid):
    return grp.getgrgid(gid).gr_name


def is_sequence(x):
    return isinstance(x, collections.abc.Sequence)


def is_sequence_except_string(x):
    return isinstance(x, collections.abc.Sequence) and not isinstance(x, str)


def is_generator(x):
    return isinstance(x, collections.abc.Generator)


def is_file(x):
    # Why not isinstance: Importing osh.file results in circular imports
    return x.__class__.__name__ == 'File'


def normalize_output(x):
    return tuple(x) if is_sequence_except_string(x) else (x,)


def clone(x):
    try:
        buffer = io.BytesIO()
        pickler = pickle.Pickler(buffer)
        print('Pickling %s' % str(x))
        pickler.dump(x)
        buffer.seek(0)
        unpickler = pickle.Unpickler(buffer)
        return unpickler.load()
    except Exception as e:
        print_stack()
        # print('Cloning error: (%s) %s' % (type(e), e))


def print_stack():
    exception_type, exception, trace = sys.exc_info()
    print('Caught %s: %s' % (exception_type, exception))
    traceback.print_tb(trace)


class Stack:

    def __init__(self):
        self.contents = []

    def push(self, x):
        self.contents.append(x)

    def top(self):
        return self.contents[-1]

    def pop(self):
        top = self.top()
        self.contents = self.contents[:-1]
        return top

    def is_empty(self):
        return len(self.contents) == 0
