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
{L,wrap=F}union PIPELINE

{L,indent=4:28}{r:PIPELINE}                The second input to the union.

The output stream represents the union of the tuples in the input stream, and the tuples
from the {r:PIPELINE} argument.

Duplicates are maintained. If a given tuple appears {n:n} times in one input, and {n:m} times in
the other, then the output stream will contain {n:m+n} occurrences. The order of tuples in the
output is unspecified.
'''


def union(env, pipeline):
    """
    Create a union of a pipeline.

    Args:
        env: (todo): write your description
        pipeline: (todo): write your description
    """
    assert isinstance(pipeline, marcel.core.Pipelineable)
    return Union(env), [pipeline.create_pipeline()]


class UnionArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        """
        Initialize the environment.

        Args:
            self: (todo): write your description
            env: (todo): write your description
        """
        super().__init__('union', env)
        # str: To accommodate var names
        self.add_anon('pipeline', convert=self.check_str_or_pipeline)
        self.validate()


class Union(marcel.core.Op):

    def __init__(self, env):
        """
        Initialize the pipeline.

        Args:
            self: (todo): write your description
            env: (todo): write your description
        """
        super().__init__(env)
        self.pipeline = None
        self.pipeline_copy = None

    def __repr__(self):
        """
        Return a repr representation of a repr__.

        Args:
            self: (todo): write your description
        """
        return 'union()'

    # AbstractOp

    def setup(self):
        """
        Sets up the pipeline.

        Args:
            self: (todo): write your description
        """
        def send_right(*x):
            """
            Sends the right.

            Args:
                x: (str): write your description
            """
            self.send(x)
        env = self.env()
        self.pipeline_copy = marcel.core.Op.pipeline_arg_value(env, self.pipeline).copy()
        self.pipeline_copy.set_error_handler(self.owner.error_handler)
        self.pipeline_copy.last_op().receiver = self.receiver

    # Op

    def receive(self, x):
        """
        Receive a message.

        Args:
            self: (todo): write your description
            x: (todo): write your description
        """
        self.send(x)

    def receive_complete(self):
        """
        Receive a complete complete.

        Args:
            self: (todo): write your description
        """
        if self.pipeline_copy is not None:
            marcel.core.Command(self.env(), None, self.pipeline_copy).execute()
            self.pipeline_copy = None
        self.send_complete()
