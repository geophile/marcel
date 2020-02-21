#!/usr/bin/python3

import sys

input = sys.stdin.read()

print('''Hello stdout 1
{}
'''.format(input), file=sys.stdout)

print('''Hello stderr 1
{}
'''.format(input), file=sys.stderr)
