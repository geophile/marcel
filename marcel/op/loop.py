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
import marcel.opmodule


HELP = '''
{L,wrap=F}loop [INITIAL_VALUE] PIPELINE

{L,indent=4:28}{r:INITIAL_VALUE}           The initial values bound to the arguments of the first op in the {r:PIPELINE}.

{L,indent=4:28}{r:PIPELINE}                The body of the loop.

Executes the given {r:PIPELINE} repeatedly. It will be clearest to explain with an example, computing Fibonacci numbers
less than 1,000,000:

{L,indent=4,wrap=T}loop ((0, 1)) [select (x, y: y < 1000000) | map (x, y: (y, x + y))] | map (x, y: x)

The loop works by carrying {r:(x, y)} pairs, representing successive Fibonacci numbers, through the pipeline.
The initial pair is {r:(0, 1)}, as specified by the {r:INITIAL_VALUE} argument.  
The last operator of the pipeline
generates the next pair to be run through the pipeline on the next loop iteration. {r:map (x, y: (y, x + y))]}
does this by computing the next pair of Fibonacci numbers. So {r:(0, 1)} -> {r:(1, 1)}. Then on the next pass, 
{r:(1, 1)} -> {r:(1, 2)}. Then {r:(1, 2)} -> {r:(2, 3)}, and so on.

If the predicate in {r:select (x, y: y < 1000000)} evaluates to false, then the {r:(x, y)} pair is not sent downstream,
no next pair is generated, and that causes the loop to terminate. I.e., this is basically a while loop.

The loop operator generates its output stream from the values that enter the pipeline, {r:(x, y)} pairs in this
example.

In this example, the {r:(x, y)} values are piped to an operator which keeps just the first item of each pair, generating
the desired output. 

If {r:INITIAL_VALUE} is omitted, then the initial value comes from the input stream, and the loop is
run to completion for each initial value in the input stream.
'''


def loop(env, init, pipeline=None):
    if pipeline is None:
        pipeline = init
        init = None
    return Loop(env), [init, pipeline.create_pipeline()]


# Argument processing is a bit odd. There are up to two arguments, init and pipeline. The FIRST of
# these, init, is optional. If omitted, the initial value comes from the input stream. If only one arg
# shows up, then assume it is a pipeline, and that initial has been omitted.
class LoopArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('loop', env)
        self.add_anon('init')
        self.add_anon('pipeline', default=None)
        self.validate()


class Loop(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.init = None
        self.pipeline = None
        self.body = None
        self.loopvar = None

    def __repr__(self):
        return f'loop({self.pipeline})' if self.init is None else f'loop({self.init} {self.pipeline})'

    # AbstractOp
    
    def setup_1(self):
        # If there is only one arg, then it should be a pipeline.
        if self.pipeline is None:
            self.pipeline = self.init
            self.init = None
        if self.init is not None:
            self.init = self.eval_function('init')
        env = self.env()
        # Find emit ops in the pipeline and connect them to self.
        loop_pipeline = marcel.core.Op.pipeline_arg_value(env, self.pipeline).copy()
        loop_pipeline.set_error_handler(self.owner.error_handler)
        op = loop_pipeline.first_op()
        while op:
            if op.op_name() == 'emit':
                op.set_loop_op(self)
            op = op.next_op
        # Attach load and store ops to implement the actual looping.
        self.loopvar = marcel.core.LoopVar(loop_pipeline)
        loop_pipeline.prepend(marcel.opmodule.create_op(env, 'load', self.loopvar))
        loop_pipeline.append(marcel.opmodule.create_op(env, 'store', self.loopvar))
        self.body = loop_pipeline

    def receive(self, x):
        if self.init is None:
            self.loopvar.append(x)
        else:
            self.loopvar.append(self.init)
        marcel.core.Command(None, self.body).execute()
