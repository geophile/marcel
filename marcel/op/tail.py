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


HELP = '''
{L,wrap=F}tail N

{L,indent=4:28}{r:N}                       The number of input tuples to be written to output.

Output the last {r:N} tuples of the input stream, and discard the others.  
'''


def tail(env, n):
    return Tail(env), [n]


class TailArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('tail', env)
        self.add_anon('n', convert=self.str_to_int, target='n_arg')
        self.validate()


class Tail(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.n_arg = None
        self.n = None
        self.queue = None  # Circular queue
        self.end = None  # End of the queue

    def __repr__(self):
        return f'tail({self.n})'

    # AbstractOp
    
    def setup(self):
        self.n = self.eval_function('n_arg', int)
        self.queue = None if self.n == 0 else [None] * self.n
        self.end = 0

    def receive(self, x):
        if self.queue:
            self.queue[self.end] = x
            self.end = self.next_position(self.end)

    def receive_complete(self):
        if self.queue is not None:
            p = self.end
            count = 0
            while count < self.n:
                x = self.queue[p]
                if x is not None:
                    self.send(x)
                p = self.next_position(p)
                count += 1
            self.queue = None
        self.send_complete()

    # For use by this class

    def next_position(self, x):
        return (x + 1) % self.n
