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


import multiprocessing as mp
import os
import tempfile
import dill
import pickle


# def share_temp(t):
#     print(f'{os.getpid()}: read t')
#     t.seek(0)
#     x = t.read()
#     print(x)
#
#
# print(f'{os.getpid()}: write t')
# t = tempfile.TemporaryFile()
# t.write(bytes('abc\n', 'utf-8'))
# t.write(bytes('def', 'utf-8'))
# p = mp.Process(target=share_temp, args=(t,))
# p.start()
# p.join()

t = tempfile.TemporaryFile()
t.write(bytes('abc\n', 'utf-8'))
t.write(bytes('def', 'utf-8'))
t_copy = pickle.loads(pickle.dumps(t))
t_copy.seek(0)
print(t_copy.read())