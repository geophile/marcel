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

import io
import pickle
import time

import dill

N = 10000


def thing(x):
    return [x, str(x), (x, x, x)]

start = time.time()
buffer = io.BytesIO()
for i in range(N):
    pickle.dump(thing(i), buffer)
buffer.seek(0)
try:
    while True:
        pickle.load(buffer)
except EOFError:
    pass
stop = time.time()
print(f'pickle: {stop - start}')

start = time.time()
buffer = io.BytesIO()
for i in range(N):
    dill.dump(thing(i), buffer)
buffer.seek(0)
try:
    while True:
        dill.load(buffer)
except EOFError:
    pass
stop = time.time()
print(f'dill: {stop - start}')