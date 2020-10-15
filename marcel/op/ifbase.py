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

import types

import marcel.argsparser
import marcel.core
import marcel.util


class IfBaseArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env, op_name):
        super().__init__(op_name, env)
        self.add_anon('predicate', convert=self.function)
        self.add_anon('then', convert=self.check_str_or_pipeline)
        self.validate()


class IfBase(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.predicate = None
        self.then = None

    def __repr__(self):
        return f'{self.op_name()})({self.predicate.snippet()} {self.then})'

    # AbstractOp

    def setup(self):
        # Copy in case caller depends on internal state
        self.then = self.then.copy()
        self.then.set_error_handler(self.owner.error_handler)
        self.then.setup()

    def set_env(self, env):
        super().set_env(env)
        self.then.set_env(env)

    def receive(self, x):
        assert False

    def receive_complete(self):
        self.then.receive_complete()
        self.send_complete()
