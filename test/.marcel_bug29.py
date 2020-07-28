from math import *
import datetime

def longer(x, y):
    if len(x) > len(y):
        return x
    else:
        return y

def todate(t):
    if t > (1 << 31):
        t = int(t / 1000)
    return datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')
    
def timestamp(x):
    return datetime.datetime.strptime(x + "000", '%Y-%m-%d %H:%M:%S.%f').strftime('%s')

define_remote(name='jao',
              user='jao',
              identity='/home/jao/.ssh/id_rsa',
              host='localhost')

