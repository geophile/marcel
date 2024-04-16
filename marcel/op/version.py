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
import marcel.version


HELP = '''
{L,wrap=F}version

Write the marcel version number to the output stream.
'''


def version():
    return Version(), []


class VersionArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('version', env)
        self.validate()


class Version(marcel.core.Op):

    def __init__(self):
        super().__init__()

    def __repr__(self):
        return 'version()'

    # AbstractOp

    def run(self, env):
        self.send(env, marcel.version.VERSION)

    # Op

    def must_be_first_in_pipeline(self):
        return True
