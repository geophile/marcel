# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, (or at your
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
import marcel.object.error
import marcel.op.redirect
import marcel.opmodule
import marcel.util

unwrap_op_output = marcel.util.unwrap_op_output

HELP = '''
{L,wrap=F}args [-a|--all] (| PIPELINE |)

{L,indent=4:28}{r:-a}, {r:--all}               Accumulate the entire input stream into a list, and bind it to a single
pipeline parameter. 

{L,indent=4:28}{r:PIPELINE}                A parameterized pipeline, to be executed with arguments coming 
from the input stream.

Items in the input stream to {r:args} will be bound to {r:PIPELINE}'s parameters. 

If {r:--all} is not specified, and the {r:PIPELINE}
has {i:n} parameters, then {i:n} items from the input stream will be used on each execution of {r:PIPELINE}.
If the input stream is exhausted after providing at least 1 but less than {i:n} arguments, remaining parameters
will be bound to {n:None}. 

If {r:--all} is specified, then the {r:PIPELINE} must have exactly one parameter. All inputs will be
accumulated into a list and bound to that parameter.
'''


def args(pipeline_function, all=False):
    assert callable(pipeline_function), pipeline_function
    op_args = ['--all'] if all else []
    op_args.append(pipeline_function)
    return (Args()), op_args


class ArgsArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('args', env)
        self.add_flag_no_value('all', '-a', '--all')
        self.add_anon('pipelines', convert=self.check_pipeline, target='pipeline_arg')
        self.validate()


class Args(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.all = None
        self.pipeline_arg = None
        self.n_params = None
        self.args = None
        self.pipeline = None

    def __repr__(self):
        flags = 'all, ' if self.all else ''
        return f'args({flags}{self.pipeline_arg})'

    # AbstractOp

    def setup(self, env):
        pipeline_arg = self.pipeline_arg
        assert (callable(pipeline_arg) or  # API
                isinstance(pipeline_arg, marcel.core.PipelineExecutable))  # CLI
        self.pipeline = marcel.core.Pipeline.create(pipeline_arg, self.customize_pipeline)
        self.pipeline.setup(env)
        self.n_params = self.pipeline.n_params()
        self.check_args()
        self.args = []

    def receive(self, env, x):
        self.args.append(unwrap_op_output(x))
        if not self.all and len(self.args) == self.n_params:
            try:
                self.pipeline.run_pipeline(env, self.args)
            finally:
                self.args.clear()

    def flush(self, env):
        if len(self.args) > 0:
            if self.all:
                self.args = [self.args]
            else:
                while len(self.args) < self.n_params:
                    self.args.append(None)
            try:
                self.pipeline.run_pipeline(env, self.args)
            finally:
                self.args.clear()
                # Need to ensure that flush is propagated no matter what happens
                self.propagate_flush(env)
        # If there was an exception, and we flushed already, this should still be OK. Propagating a
        # flush a second time should be a noop.
        self.propagate_flush(env)

    def check_args(self):
        error = None
        if self.all and self.n_params != 1:
            error = 'With -a|--all option, the pipelines must have exactly one parameter.'
        elif self.n_params == 0:
            error = 'The args pipelines must be parameterized.'
        if error:
            raise marcel.exception.KillCommandException(error)

    def customize_pipeline(self, env, pipeline):
        pipeline.append(marcel.op.redirect.Redirect(self))
        return pipeline

