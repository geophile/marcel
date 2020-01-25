import pwd
import grp
import collections.abc


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
