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

import importlib

import marcel.argsparser
import marcel.core
import marcel.exception


HELP = '''
{L,wrap=F}import MODULE
{L,wrap=F}import MODULE *
{L,wrap=F}import MODULE SYMBOL [NAME]

{L,indent=4:28}{r:MODULE}                  Name of the module to import.

{L,indent=4:28}{r:SYMBOL}                  Name of the symbol in {r:MODULE} to import.

{L,indent=4:28}{r:NAME}                    Name to assign to the imported symbol.

Imports symbols into the marcel namespace, so that they can be used in marcel functions. The import operator
provides some but not all of the capabilities of Python's {n:import} statement. In some cases, you may need
to use multiple invocations of the operator where one statement would have sufficed.

{r:import MODULE} imports {r:MODULE} into the marcel namespace. Symbols within that module need to be qualified.
I.e., it has the same effect as the Python statement {n:import MODULE}.

{r:import MODULE *} imports all of the symbols inside {r:MODULE}, placing those symbols in the marcel
namespace. This is like running the Python statement {n:from MODULE import *}.

{r:import MODULE SYMBOL} imports just {r:SYMBOL} from {r:MODULE}, place it in the marcel namespace.
This is like running the Python statement {n:from MODULE import SYMBOL}.

{r:import MODULE SYMBOL NAME} imports just {r:SYMBOL}, but places it in the marcel namespace under {r:NAME}.
I.e., it is like running {n:from MODULE import SYMBOL as NAME}.
'''


class ImportArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('head', env)
        self.add_anon('module')
        self.add_anon('symbol', default=None)
        self.add_anon('name', default=None)
        self.validate()


class Import(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.module = None
        self.symbol = None
        self.name = None

    def __repr__(self):
        buffer = [f'import({self.module}']
        if self.symbol:
            buffer.append(f', {self.symbol}')
        if self.name:
            buffer.append(f', {self.name}')
        buffer.append(')')
        return ''.join(buffer)

    # AbstractOp
    
    def setup(self):
        if self.symbol and not (self.symbol == '*' or self.symbol.isidentifier()):
            raise marcel.exception.KillCommandException(f'symbol must be * or a valid identifier: {self.symbol}')
        if self.name and not self.name.isidentifier():
            raise marcel.exception.KillCommandException(f'name is not a valid identifier: {self.name}')

    def run(self):
        env = self.env()
        try:
            module = importlib.import_module(self.module)
        except ModuleNotFoundError:
            self.fatal_error(None, f'Module {self.module} not found.')
        if self.symbol is None:
            env.setvar(self.module, module)
        elif self.symbol == '*':
            for key, value in module.__dict__.items():
                if not key.startswith('_'):
                    env.setvar(key, value)
        else:
            try:
                value = module.__dict__[self.symbol]
                name = self.name if self.name else self.symbol
                env.setvar(name, value)
            except KeyError:
                self.non_fatal_error(message=f'{self.symbol} is not defined in {self.module}')

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True
