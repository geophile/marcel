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
import marcel.exception


HELP = '''
{L,wrap=F}tail N

{L,indent=4:28}{r:N}                       The number of input tuples to be written to output, or skipped
(depending on the sign).

If {r:N} > 0, then output the last {r:N} tuples of the input stream, and discard the others.  

If {r:N} < 0, then skip the last {r:N} tuples of the input stream, and output the others. (I.e.,
output all but the last {r:N} tuples.)
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
        self.impl = None

    def __repr__(self):
        return f'tail({self.n_arg})'

    # AbstractOp
    
    def setup(self):
        n = self.eval_function('n_arg', int)
        if n == 0:
            raise marcel.exception.KillCommandException('Argument to head must not be 0.')
        self.impl = TailKeepN(self, n) if n > 0 else TailSkipN(self, -n)

    def receive(self, x):
        self.impl.receive(x)

    def receive_complete(self):
        self.impl.receive_complete()


class TailImpl:

    def __init__(self, op, n):
        self.op = op
        self.n = n
        self.queue = []  # Circular queue
        self.end = 0  # End of the queue

    def receive(self, x):
        assert False

    def receive_complete(self):
        assert False


class TailKeepN(TailImpl):

    def __init__(self, op, n):
        super().__init__(op, n)

    def receive(self, x):
        if len(self.queue) < self.n:
            self.queue.append(x)
        else:
            self.queue[self.end] = x
            self.end = (self.end + 1) % self.n

    def receive_complete(self):
        p = self.end
        count = min(self.n, len(self.queue))
        while count > 0:
            x = self.queue[p]
            if x is not None:
                self.op.send(x)
            p = (p + 1) % self.n
            count -= 1
        self.op.send_complete()
        self.queue.clear()


class TailSkipN(TailImpl):

    def __init__(self, op, n):
        super().__init__(op, n)

    def receive(self, x):
        if len(self.queue) < self.n:
            self.queue.append(x)
        else:
            self.op.send(self.queue[self.end])
            self.queue[self.end] = x
            self.end = (self.end + 1) % self.n

    def receive_complete(self):
        pass
