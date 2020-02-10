#!/usr/bin/python3

import sys

print('''Hello stdout 1
Hello stdout 2
''', file=sys.stdout)

print('''Hello stderr 1
Hello stderr 2
''', file=sys.stderr)
