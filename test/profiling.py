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
import time

from marcel.api import *

# start = time.time()
# run(ls('/tmp/d') | select(lambda *t: False))
# stop = time.time()
# print(f'ls, no output: {stop-start}')

start = time.time()
run(ls('/tmp/1') | out(file='/dev/null'))
# run(ls('/tmp/d') | out(file='/dev/null'))
stop = time.time()
print(f'ls, output to /dev/null: {stop-start}')

# start = time.time()
# run(ls('/tmp/d') | map(lambda f: (f, 1)) | select(lambda *t: False))
# stop = time.time()
# print(f'ls, output to /dev/null: {stop-start}')
#
# start = time.time()
# run(ls('/tmp/d') | map(lambda f: (f, 1)) | out(file='/dev/null'))
# stop = time.time()
# print(f'ls, output to /dev/null: {stop-start}')

