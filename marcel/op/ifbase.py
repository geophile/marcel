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
import marcel.util


class IfBaseArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env, op_name):
        super().__init__(op_name, env)
        self.add_anon('predicate', convert=self.function)
        self.add_anon('then', convert=self.check_pipeline, target='then_arg')
        self.validate()


class IfBase(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.predicate = None
        self.then_arg = None
        self.then = None

    def __repr__(self):
        return f'{self.op_name()})({self.predicate.snippet()} {self.then_arg})'

    # AbstractOp

    def setup(self, env):
        self.then = marcel.core.Pipeline.create(self.then_arg, lambda env, pipeline: pipeline)
        self.then.setup(env)
        self.then.prepare_to_receive(env)

    def receive(self, env, x):
        assert False

    def flush(self, env):
        self.then.flush(env)
        self.propagate_flush(env)

    def cleanup(self):
        self.then.cleanup()
