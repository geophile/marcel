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


SUMMARY = '''
Output the leading items of the input stream, and discard the others.  
'''


DETAILS = '''
The first {r:n} items received from the input stream will be written to the
output stream. All other input items will be discarded. 
'''


def head(env, n):
    op = Head(env)
    op.n = n
    return op


class HeadArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('head', env, None, SUMMARY, DETAILS)
        self.add_argument('n',
                          type=super().constrained_type(marcel.core.ArgParser.check_non_negative,
                                                        'must be non-negative'),
                          help='The number of input items to keep.')


class Head(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.n = None
        self.received = None

    def __repr__(self):
        return f'head({self.n})'

    # BaseOp
    
    def setup_1(self):
        self.received = 0

    def receive(self, x):
        self.received += 1
        if self.n >= self.received:
            self.send(x)
