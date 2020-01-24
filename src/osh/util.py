import pwd
import grp
import collections.abc


def username(uid):
    return pwd.getpwuid(uid).pw_name


def groupname(gid):
    return grp.getgrgid(gid).gr_name


def is_sequence(x):
    return isinstance(x, collections.abc.Sequence)


def is_generator(x):
    return isinstance(x, collections.abc.Generator)


def is_file(x):
    # Why not isinstance: Importing osh.file results in circular imports
    return x.__class__.__name__ == 'File'


def normalize_output(x):
    return x if is_sequence(x) else (x,)
    # if not is_sequence(x):
    #     x = (x,)
    # return tuple(x)
