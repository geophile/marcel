# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or at your
# option) any later version.
# 
# Marcel is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Marcel.  If not, see <https://www.gnu.org/licenses/>.

import os
import pathlib
import signal
import subprocess
import time

DEPTH = 3
COUNTER_FILE = '/tmp/counter.txt'
PID = os.getpid()


class Counter:

    def __init__(self, path):
        self.path = path
        if not pathlib.Path(path).exists():
            self.write(0)

    def read(self):
        with open(self.path, 'r') as count_file:
            return int(count_file.readlines()[0].strip())

    def write(self, x):
        with open(self.path, 'w') as count_file:
            count_file.writelines([str(x)])


def spawn():
    process = subprocess.Popen('python3 signal_propagation.py',
                               shell=True,
                               executable='/bin/bash',
                               universal_newlines=True)
    while True:
        try:
            process.wait(1)
            break
        except subprocess.TimeoutExpired:
            print(f'Process {PID} waiting')
    if process.returncode != 0:
        print(f'Escaped command failed with exit code {process.returncode}')


def main():
    counter = Counter(COUNTER_FILE)
    n = counter.read() + 1  # + 1: this process
    print(f'process {PID}: counter = {n}')
    if n == 1:
        signal.signal(signal.SIGTSTP, signal.SIG_DFL)
    if n < DEPTH:
        counter.write(n)
        spawn()
    else:
        while True:
            time.sleep(1)
            print(f'Process {PID} sleeping')


main()
