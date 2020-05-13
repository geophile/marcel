import datetime as dt
import time
import pathlib

offset = time.strftime('%z')

sign = offset[0]
if sign == '-':
    p = 1
    while p < len(offset) and offset[p] == '0':
        p += 1
    assert p < len(offset)
    hours_offset = -int(offset[p:]) / 100
elif sign == '+':
    p = 1
    while p < len(offset) and offset[p] == '0':
        p += 1
    if p == len(offset):
        # +0000
        hours_offset = 0
    else:
        hours_offset = int(offset[p:]) / 100
else:
    assert False
tz = dt.timezone(dt.timedelta(hours=hours_offset))

# # With timezone
# now = dt.datetime.now(tz)
# file_mtime = pathlib.Path('/home/jao/Downloads').stat().st_mtime
# file_datetime = dt.datetime.fromtimestamp(file_mtime, tz)
# delta = now - file_datetime
# print(delta)
#
# # Without timezone
# now = dt.datetime.now()
# file_mtime = pathlib.Path('/home/jao/Downloads').stat().st_mtime
# file_datetime = dt.datetime.fromtimestamp(file_mtime)
# delta = now - file_datetime
# print(delta)
# print(type(delta))

p = pathlib.Path('/home/jao/git/marcel/test/test_ops.py')
file_mtime = p.stat().st_mtime
now = time.time()

print(f'now - file_mtime: {now - file_mtime}')
print(f'delta as timedelta: {dt.timedelta(seconds=now - file_mtime)}')
print(f'now as datetime: {dt.datetime.fromtimestamp(now)}')
print(f'file mtime as datetime: {dt.datetime.fromtimestamp(file_mtime)}')