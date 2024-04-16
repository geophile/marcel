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

import contextlib
import importlib
import io

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.helpformatter
import marcel.util

HELP = '''
{L}help [TOPIC]

{L,indent=4:28}{r:TOPIC}             A marcel operator or concept.

Prints information on some aspect of marcel. If {r:TOPIC} is not provided, then a top-level introduction
is printed, along with suggestions for further exploration. {r:TOPIC} may be a marcel operator, or a concept
mentioned in some other help message. 
'''


def help():
    return Help()


class HelpArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('help', env)
        self.add_anon('topic', convert=self.check_str, default='marcel')
        self.validate()


class Help(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.topic = None
        self.module = None

    def __repr__(self):
        return f'help({self.topic})'

    # AbstractOp
    
    def setup(self, env):
        self.topic = self.topic.lower()

    def run(self, env):
        op_module = env.op_modules.get(self.topic, None)
        help_text = Help.op_help(env, op_module) if op_module else self.topic_help(env)
        self.send(env, help_text)
        self.send(env, '')

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True

    # For use by this class

    @staticmethod
    def op_help(env, op_module):
        help_text = op_module.help()
        formatter = marcel.helpformatter.HelpFormatter(env.color_scheme())
        return formatter.format(help_text)

    def topic_help(self, env):
        try:
            self.module = importlib.import_module(f'marcel.doc.help_{self.topic}')
        except ModuleNotFoundError:
            raise marcel.exception.KillCommandException(f'Help not available for {self.topic}')
        formatter = marcel.helpformatter.HelpFormatter(env.color_scheme())
        help_text = getattr(self.module, 'HELP')
        return formatter.format(help_text)
