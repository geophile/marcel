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

Op = marcel.core.Op


HELP = '''
{L,wrap=F}gen [-p|--pad PAD] [COUNT [START]]

{L,indent=4:28}{r:-p,} {r:--pad}               Specifies the width of the padded output.

{L,indent=4:28}{r:COUNT}                   The number of integers to be written to output. 

{L,indent=4:28}{r:START}                   The first integer to be written to output. 

Generates a stream of {r:COUNT} integers, starting at {r:START}.

The first integer in the stream is {r:START}. The number of integers in the stream is {r:COUNT},
although if {r:COUNT} is 0, then the stream does not terminate. If {r:PAD} is specified, 
then each integer is converted to a string and left-padded with zeros so that the 
string's length is {r:PAD}. Padding is not 
permitted if the stream does not terminate, or if {r:START} is negative.
'''


def gen(env, count=0, start=0, pad=None):
    args = ['--pad', pad] if pad else []
    args.append(count)
    args.append(start)
    return Gen(env), args


class GenArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('gen', env)
        self.add_flag_one_value('pad', '-p', '--pad', convert=self.str_to_int, target='pad_arg')
        self.add_anon('count', convert=self.str_to_int, default=0, target='count_arg')
        self.add_anon('start', convert=self.str_to_int, default=0, target='start_arg')
        self.validate()


class Gen(Op):

    def __init__(self, env):
        super().__init__(env)
        self.count_arg = None
        self.start_arg = None
        self.pad_arg = None
        self.count = None
        self.start = None
        self.format = None

    def __repr__(self):
        args = [f'count={self.count_arg}']
        if self.start_arg is not None:
            args.append(f'start={self.start_arg}')
        if self.pad_arg is not None:
            args.append(f'pad={self.pad_arg}')
        args_description = ', '.join(args)
        return f'gen({args_description})'

    # AbstractOp

    def setup(self):
        pad = self.eval_function('pad_arg', int)
        self.count = self.eval_function('count_arg', int)
        self.start = self.eval_function('start_arg', int)
        if pad is not None:
            if self.count == 0:
                raise marcel.exception.KillCommandException(f'Padding {pad} incompatible with unbounded output.')
            if self.start < 0:
                raise marcel.exception.KillCommandException(f'Padding incompatible with start < 0: {self.start}')
            max_length = len(str(self.start + self.count - 1))
            if max_length > pad:
                raise marcel.exception.KillCommandException(f'Padding {pad} too small.')
            self.format = '{:>0' + str(pad) + '}'

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
