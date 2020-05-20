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

import marcel.core
import marcel.functionwrapper


SUMMARY = '''
The input stream is sorted and written to the output stream.
'''


DETAILS = '''
If {r:key} is not specified, then input tuples are ordered according to Python rules.
Otherwise, ordering is based on the values computed by applying {r:key} to each input tuple.
'''


def sort(env, key=None):
    op = Sort(env)
    op.key = None if key is None else marcel.functionwrapper.FunctionWrapper(function=key)
    return op


class SortArgParser(marcel.core.ArgParser):
    
    def __init__(self, env):
        super().__init__('sort', env, None, SUMMARY, DETAILS)
        self.add_argument('key',
                          nargs='?',
                          default=None,
                          type=super().constrained_type(self.check_function, 'not a valid function'),
                          help='Function to obtain the value used for ordering.')


class Sort(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.key = None
        self.contents = None

    def __repr__(self):
        return 'sort'

    # BaseOp
    
    def setup_1(self):
        self.contents = []
        if self.key:
            self.key.set_op(self)

    def receive(self, x):
        self.contents.append(x)
    
    def receive_complete(self):
        if self.key:
            self.contents.sort(key=lambda t: self.key(*t))
        else:
            self.contents.sort()
        for x in self.contents:
            self.send(x)
        self.send_complete()
