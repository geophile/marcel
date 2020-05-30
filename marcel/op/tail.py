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

import marcel.argsparser
import marcel.core


SUMMARY = '''
Output the trailing items of the input stream, and discard the others.  
'''


DETAILS = '''
The last {r:n} items received from the input stream will be written to the
output stream. All other input items will be discarded. 
'''


def tail(env, n):
    return Tail(env), [n]


class TailArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('tail', env)
        self.add_anon('n', convert=self.str_to_int)
        self.validate()


class Tail(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.n = None
        self.queue = None  # Circular queue
        self.end = None  # End of the queue

    def __repr__(self):
        return f'tail({self.n})'

    # BaseOp
    
    def setup_1(self):
        self.eval_functions('n')
        self.queue = None if self.n == 0 else [None] * self.n
        self.end = 0

    def receive(self, x):
        if self.queue:
            self.queue[self.end] = x
            self.end = self.next_position(self.end)

    def receive_complete(self):
        if self.queue:
            p = self.end
            count = 0
            while count < self.n:
                x = self.queue[p]
                if x is not None:
                    self.send(x)
                p = self.next_position(p)
                count += 1

    # For use by this class

    def next_position(self, x):
        return (x + 1) % self.n
