import pwd
import grp


def normalize_output(x):
    if not(isinstance(x, tuple) or isinstance(x, list)):
        x = (x,)
    return tuple(x)


def username(uid):
    return pwd.getpwuid(uid).pw_name


def groupname(gid):
    return grp.getgrgid(gid).gr_name
