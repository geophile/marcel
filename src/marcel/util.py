import collections.abc
import grp
import io
import pathlib
import pickle
import pwd
import sys
import time
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
        pickler.dump(x)
        buffer.seek(0)
        unpickler = pickle.Unpickler(buffer)
        copy = unpickler.load()
        return copy
    except Exception as e:
        print('Cloning error: (%s) %s' % (type(e), e), file=sys.__stderr__)
        print_stack()


def print_stack(file=None):
    if file is None:
        file = sys.__stderr__
    exception_type, exception, trace = sys.exc_info()
    print('Caught %s: %s' % (exception_type, exception), file=file)
    traceback.print_tb(trace, file=file)


def colorize(s, color):
    return (s
            if color is None else
            '\033[%sm\033[38;5;%sm%s\033[0m' % (1 if color.bold else 0, color.code, s))


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


class Trace:

    def __init__(self, tracefile):
        self.path = pathlib.Path(tracefile)
        self.path.touch(mode=0o666, exist_ok=True)
        self.path.unlink()
        self.file = self.path.open(mode='w')

    def write(self, line):
        print('%s: %s' % (time.time(), line), file=self.file, flush=True)

    def close(self):
        self.file.close()
