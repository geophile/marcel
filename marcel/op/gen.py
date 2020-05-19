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
Generates a stream of {r:count} integers, starting at {r:start}.
'''


DETAILS = '''
The first integer in the stream is {r:start}. The number of integers in the stream is {r:count},
although if {r:count} is 0, then the stream does not terminate. If {r:pad} is specified, 
then each integer is converted to a string and left-padded with zeros. Padding is not 
permitted if the stream does not terminate, or if {r:start} is negative.
'''


def gen(env, count=0, start=0, pad=None):
    op = Gen(env)
    op.count = count
    op.start = start
    op.pad = pad
    return op


class GenArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('gen', env, ['-p', '--pad'], SUMMARY, DETAILS)
        self.add_argument('-p', '--pad',
                          type=int,
                          help='Left-pad with zeros to PAD characters')
        self.add_argument('count',
                          nargs='?',
                          default='0',
                          type=int,
                          help='''The number of integers to generate. Must be non-negative.
                          Default value is 0. 
                          If 0, then the sequence does not terminate''')
        self.add_argument('start',
                          nargs='?',
                          default='0',
                          type=int,
                          help='The first integer in the stream. Default value is 0.')


class Gen(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.pad = None
        self.count = None
        self.start = None
        self.format = None

    def __repr__(self):
        return f'gen(count={self.count}, start={self.start}, pad={self.pad})'

    # BaseOp

    def setup_1(self):
        if self.pad is not None:
            super().check_arg(self.count >= 0, 'count', 'Padding incompatible with unbounded output.')
            super().check_arg(self.start >= 0, 'start', 'Padding incompatible with start < 0.')
            max_length = len(str(self.start + self.count - 1))
            super().check_arg(max_length <= self.pad, 'pad', 'Padding too small.')
            self.format = '{:>0' + str(self.pad) + '}'

    def receive(self, _):
        if self.count is None or self.count == 0:
            x = self.start
            while True:
                self.send(self.apply_padding(x))
                x += 1
        else:
            for x in range(self.start, self.start + self.count):
                self.send(self.apply_padding(x))

    # Op

    def must_be_first_in_pipeline(self):
        return True

    # For use by this class

    def apply_padding(self, x):
        return (self.format.format(x)) if self.format else x
