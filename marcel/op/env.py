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


SUMMARY = '''
Write the contents of the marcel namespace to the output stream.
'''


DETAILS = '''
The marcel namespace is a Python {n:dict}. Each key/value pair is written to the output stream as a tuple,
(key, value), sorted by key. Python's {n:__builtins__} is part of the marcel namespace, but is omitted
from output. 
'''


def env(env):
    return Env(env), []


class EnvArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('env', env)
        self.validate()


class Env(marcel.core.Op):

    OMITTED = ['__builtins__']

    def __init__(self, env):
        super().__init__(env)

    def __repr__(self):
        return 'env()'

    # BaseOp

    def receive(self, _):
        for key, value in sorted(self.env().namespace.items()):
            if key not in Env.OMITTED:
                self.send((key, value))

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True
