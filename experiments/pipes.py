import os
import sys

r, w = os.pipe()
print('MAIN: pid = {}, stdout = {}, stderr = {}, r = {}, w = {}'.format(
    os.getpid(), sys.stdout.fileno(), sys.stderr.fileno(), r, w))
pid = os.fork()
if pid > 0:
    # parent
    print('PARENT: pid = {}, os.getpid = {}, stdout = {}, stderr = {}'.format(
        pid, os.getpid(), sys.stdout.fileno(), sys.stderr.fileno()))
    os.close(r)
    text = b"Hello child process"
    os.write(w, text)
    print("PARENT: Written text:", text.decode())
else:
    # child
    print('CHILD: pid = {}, os.getpid = {}, stdout = {}, stderr = {}'.format(
        pid, os.getpid(), sys.stdout.fileno(), sys.stderr.fileno()))
    os.close(w)
    # Read the text written by parent process
    print("CHILD: Child Process is reading")
    r = os.fdopen(r)
    print("CHILD: Read text:", r.read())
