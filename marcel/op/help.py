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

import contextlib
import importlib
import io

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.helpformatter
import marcel.util


def help(env):
    """
    Return the help

    Args:
        env: (todo): write your description
    """
    return Help(env)


class HelpArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        """
        Initialize the environment.

        Args:
            self: (todo): write your description
            env: (todo): write your description
        """
        super().__init__('help', env)
        self.add_anon('topic', convert=self.check_str, default='marcel')
        self.validate()


class Help(marcel.core.Op):

    def __init__(self, env):
        """
        Initialize the environment.

        Args:
            self: (todo): write your description
            env: (todo): write your description
        """
        super().__init__(env)
        self.topic = None
        self.module = None

    def __repr__(self):
        """
        Return a repr representation of a repr__.

        Args:
            self: (todo): write your description
        """
        return f'help({self.topic})'

    # AbstractOp
    
    def setup(self):
        """
        Initialize the topic.

        Args:
            self: (todo): write your description
        """
        self.topic = self.topic.lower()

    def receive(self, _):
        """
        Receive a message.

        Args:
            self: (todo): write your description
            _: (todo): write your description
        """
        op_module = self.env().op_modules.get(self.topic, None)
        help_text = self.op_help(op_module) if op_module else self.topic_help()
        self.send(help_text)
        self.send('')

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

    # For use by this class

    def op_help(self, op_module):
        """
        Return the help text for the given operation.

        Args:
            self: (todo): write your description
            op_module: (todo): write your description
        """
        help_text = op_module.help()
        formatter = marcel.helpformatter.HelpFormatter(self.env().color_scheme())
        return formatter.format(help_text)

    def topic_help(self):
        """
        Return the help string for the topic.

        Args:
            self: (todo): write your description
        """
        try:
            self.module = importlib.import_module(f'marcel.doc.help_{self.topic}')
        except ModuleNotFoundError:
            raise marcel.exception.KillCommandException(f'Help not available for {self.topic}')
        formatter = marcel.helpformatter.HelpFormatter(self.env().color_scheme())
        help_text = getattr(self.module, 'HELP')
        return formatter.format(help_text)
