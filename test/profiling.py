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

import time

from marcel.api import*

N = 1000000
start = time.time()
run(gen(N) | map(lambda x: x+1) | map(lambda x: x+1) | map(lambda x: x+1) | select(lambda x: False))
stop = time.time()
usec = (stop - start) * 1000000 / N
print(f'{usec} usec per unit')

