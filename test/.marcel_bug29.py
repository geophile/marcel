from math import *
import datetime

def longer(x, y):
    """
    Returns the longitude of x.

    Args:
        x: (todo): write your description
        y: (todo): write your description
    """
    if len(x) > len(y):
        return x
    else:
        return y

def todate(t):
    """
    Return a datetime.

    Args:
        t: (todo): write your description
    """
    if t > (1 << 31):
        t = int(t / 1000)
    return datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')
    
def timestamp(x):
    """
    Convert timestamp.

    Args:
        x: (int): write your description
    """
    return datetime.datetime.strptime(x + "000", '%Y-%m-%d %H:%M:%S.%f').strftime('%s')

define_remote(name='jao',
              user='jao',
              identity='/home/jao/.ssh/id_rsa',
              host='localhost')

