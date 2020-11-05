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

HELP = '''
{L,wrap=F}env [-a|--all] [-b|--builtin] [-c|--config] [-s|--session]

{L,indent=4:28}{r:-a}, {r:--all}               Output all symbols defined in the environment.

{L,indent=4:28}{r:-b}, {r:--builtin}           Output only builtin symbols.

{L,indent=4:28}{r:-c}, {r:--config}            Output only symbols defined in the configuration file, {n:~/.marcel.py}.

{L,indent=4:28}{r:-s}, {r:--session}           Output only symbols defined during the current session.

Write the contents of the environment, (i.e., the marcel namespace), to the output stream.
Each key/value pair is written to the output stream as a tuple,
(key, value), sorted by key. Python's {n:__builtins__} is part of the marcel namespace, but is omitted
from output. 

If the {r:--all} flag is provided, then all symbols in the environment (except those in Python's {n:__builtins__})
are output. This is the default behavior. The {r:--all} flag cannot be combined with others. 

If the {r:--builtin} flag is provided, then the symbols defined by marcel are output. This excludes symbols
defined in the config file ({n:~/.marcel.py}), and those defined in the current session, e.g. by assigning to
a previously undefined environment variable.

If the {r:--config} flas is provided, then the symbols defined in the config file ({n:~/.marcel.py}) are output.

If the {r:--session} flag is provided, then the symbols defined in the current session are provided. These are variables
that obtain their value by assignment, (e.g. {n:answer = (42)}), or by storing a stream, (e.g. {n:ls -fr > files}).

Default behavior, (i.e., no flags are specified) is the same as {r:--all}. This is also equivalent to specifying
all of {r:--builtin}, {r:--config}, and {r:--session}. Those three flags can also be combined. E.g, using
the short flag names, {r:-cs} would get all symbols except the builtin ones.
'''


def env(env):
    """
    Return the environment variable.

    Args:
        env: (todo): write your description
    """
    return Env(env), []


class EnvArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        """
        This function to env.

        Args:
            self: (todo): write your description
            env: (todo): write your description
        """
        super().__init__('env', env)
        self.add_flag_no_value('all', '-a', '--all')
        self.add_flag_no_value('builtin', '-b', '--builtin')
        self.add_flag_no_value('config', '-c', '--config')
        self.add_flag_no_value('session', '-s', '--session')
        self.at_most_one('all', 'builtin')
        self.at_most_one('all', 'config')
        self.at_most_one('all', 'session')
        self.validate()


class Env(marcel.core.Op):
    OMITTED = ['__builtins__']

    def __init__(self, env):
        """
        Initialize the environment.

        Args:
            self: (todo): write your description
            env: (todo): write your description
        """
        super().__init__(env)
        self.all = None
        self.builtin = None
        self.config = None
        self.session = None

    def __repr__(self):
        """
        Return a string representation of this object.

        Args:
            self: (todo): write your description
        """
        flags = ''
        if self.builtin:
            flags += 'b'
        if self.config:
            flags += 'c'
        if self.session:
            flags += 's'
        return f'env({flags})'

    # AbstractOp

    def setup(self):
        """
        Setup the session.

        Args:
            self: (todo): write your description
        """
        if not(self.all or self.builtin or self.config or self.session):
            # No flags specified. Default behiavor is all.
            self.all = True
        if self.all:
            self.builtin = True
            self.config = True
            self.session = True

    def receive(self, _):
        """
        Receive a new environment.

        Args:
            self: (todo): write your description
            _: (todo): write your description
        """
        builtin_symbols = self.env().builtin_symbols
        config_symbols = self.env().config_symbols
        for key, value in sorted(self.env().vars().items()):
            if key not in Env.OMITTED:
                key_builtin = key in builtin_symbols
                key_config = key in config_symbols
                if (self.builtin and key_builtin or
                        self.config and key_config or
                        self.session and not (key_builtin or key_config)):
                    self.send((key, value))

    # Op

    def must_be_first_in_pipeline(self):
        """
        Returns true if the pipeline is in the pipeline.

        Args:
            self: (todo): write your description
        """
        return True

    def run_in_main_process(self):
        """
        Runs a list of - main loop.

        Args:
            self: (todo): write your description
        """
        return True
