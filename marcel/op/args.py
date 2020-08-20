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
import marcel.opmodule
import marcel.object.error
import marcel.util

HELP = '''
{L,wrap=F}args PIPELINE

{L,indent=4:28}{r:PIPELINE}                The pipeline to be executed with arguments coming from the {r:args}
operator's input stream.

Items in the input stream to {r:args} will be bound to the {r:PIPELINE}s parameters. 

If the {r:PIPELINE}
has {i:n} parameters, then {i:n} items from the input stream will be used on each execution of {r:PIPELINE}.
If the input stream is exhausted after providing at least 1 but less than {i:n} arguments, remaining arguments
will be bound to {n:None}. 
'''


def args(env, pipeline):
    # assert isinstance(pipeline, marcel.core.Pipelineable), type(pipeline)
    return Args(env), [pipeline.create_pipeline()]


class ArgsArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('args', env)
        # str: To accommodate var names
        self.add_anon('pipeline', convert=self.check_str_or_pipeline)
        self.validate()


class Args(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.pipeline = None
        self.pipeline_copy = None
        self.n_params = None
        self.args = None

    def __repr__(self):
        return 'args()'

    # AbstractOp

    def setup_1(self):
        def send_pipeline_output(*x):
            self.send(x)
        if self.pipeline.parameters() is None:
            raise marcel.exception.KillCommandException('The args pipeline must be parameterized.')
        self.pipeline_copy = self.pipeline_arg(self.pipeline).copy()
        self.pipeline_copy.set_error_handler(self.owner.error_handler)
        self.pipeline_copy.append(marcel.opmodule.create_op(self.env(), 'map', send_pipeline_output))
        self.n_params = len(self.pipeline.parameters())
        self.args = []

    def receive(self, x):
        self.args.append(marcel.util.unwrap_op_output(x))
        if len(self.args) == self.n_params:
            self.pipeline_copy.set_parameter_values(self.args, None)
            marcel.core.Command(None, self.pipeline_copy).execute()
            self.args.clear()

    def receive_complete(self):
        if len(self.args) > 0:
            while len(self.args) < self.n_params:
                self.args.append(None)
            self.pipeline_copy.set_parameter_values(self.args, None)
            marcel.core.Command(None, self.pipeline_copy).execute()
