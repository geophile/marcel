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
import marcel.exception
import marcel.object.error
import marcel.util

SUMMARY = '''
Computes a database-style join between the incoming stream, 
and the input stream from a second pipeline.
'''

DETAILS = '''
The input pipeline provides one input to the join, named {i:left}.
The {r:pipeline} argument provides the second input, named {i:right}.
Left and right tuples are matched by comparing the first component. For matching
pairs, an output tuple consists of the left input followed by the right row with the
first value removed. (That would be redundant since the tuples were matched on their
first values.)

The {r:--keep} flag causes left inputs to be passed to output as is, when there is no
matching right input. (In database terms, this is a left join.)

{b:Example}

The left input has 12 tuples of the form {n:(x, -x)}, generated by {n:gen 12 | map (x: (x, -x))}.
The right input has 10 tuples of the form {n:(x, x**2)}, generated by {n:gen 10 | map (x: (x, x**2))}.
The join is computed as follows:

{L,wrap=F}gen 12 | map (x: (x, -x)) | join [ gen 10 | map (x: (x, x**2)) ]

This generates the following output:

{L,wrap=F,indent=4}
(0, 0, 0)
(1, -1, 1)
(2, -2, 4)
(3, -3, 9)
(4, -4, 16)
(5, -5, 25)
(6, -6, 36)
(7, -7, 49)
(8, -8, 64)
(9, -9, 81)

If the {r:--keep} flag were included, the output would have two additional rows:

{L,wrap=F,indent=4}
(0, 0, 0)
(1, -1, 1)
(2, -2, 4)
(3, -3, 9)
(4, -4, 16)
(5, -5, 25)
(6, -6, 36)
(7, -7, 49)
(8, -8, 64)
(9, -9, 81)
(10, -10)
(11, -11)
'''


def join(env, pipeline, keep=False):
    op = Join(env)
    op.pipeline = pipeline
    op.keep = keep
    return op


class JoinArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('join', env, [], SUMMARY, DETAILS)
        self.add_argument('-k', '--keep', action='store_true')
        self.add_argument('pipeline')


class Join(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.pipeline = None
        self.keep = None
        self.pipeline_map = None  # Map containing contents of pipeline, keyed by join value

    def __repr__(self):
        return 'join(keep)' if self.keep else 'join()'

    # BaseOp

    def setup_1(self):
        def load_pipeline_map(*x):
            join_value = x[0]
            match = self.pipeline_map.get(join_value, None)
            if match is None:
                self.pipeline_map[join_value] = x
            elif type(match) is list:
                match.append(x)
            else:
                # match is first value associated with join_value, x is the second. Need a list.
                self.pipeline_map[join_value] = [match, x]
        self.pipeline_map = {}
        pipeline = self.resolve_pipeline_reference(self.pipeline)
        pipeline.set_error_handler(self.owner.error_handler)
        op = self.env().op_modules['map'].api_function()(self.env, load_pipeline_map)
        pipeline.append(op)
        marcel.core.Command(None, pipeline).execute()

    def receive(self, x):
        join_value = x[0]
        match = self.pipeline_map.get(join_value, None)
        if match is None:
            if self.keep:
                self.send(x)
        elif type(match) is list:
            for m in match:
                self.send(x + m[1:])
        else:
            self.send(x + match[1:])