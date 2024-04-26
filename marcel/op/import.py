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
import marcel.exception


HELP = '''
{L,wrap=F}import [-a|--as NAME] MODULE 
{L,wrap=F}import [-a|--as NAME] MODULE SYMBOL 
{L,wrap=F}import MODULE *

{L,indent=4:28}{r:MODULE}                  Name of the module to import.

{L,indent=4:28}{r:SYMBOL}                  Name of the symbol in {r:MODULE} to import.

{L,indent=4:28}{r:-a}, {r:--as} {r:NAME}           Name to assign to the imported symbol.

Imports symbols into the marcel namespace, so that they can be used in marcel functions. The {r:import} operator
provides some but not all of the capabilities of Python's {n:import} statement. In some cases, you may need
to use multiple invocations of the operator where one statement would have sufficed.

{r:import MODULE} imports {r:MODULE} into the marcel namespace. Symbols within that module need to be qualified.
I.e., it has the same effect as the Python statement {n:import MODULE}.

{r:import MODULE SYMBOL} imports just {r:SYMBOL} from {r:MODULE}, place it in the marcel namespace.
This is like running the Python statement {n:from MODULE import SYMBOL}.

{r:--as} changes the name of the symbol being imported. So {n:import MODULE --as NAME} is like the Python
statement {n:import MODULE as NAME}, and {n:import MODULE SYMBOL --as NAME} is like
{n:from MODULE import SYMBOL as NAME}

{r:import MODULE *} imports all of the symbols inside {r:MODULE}, placing those symbols in the marcel
namespace. This is like running the Python statement {n:from MODULE import *}.
'''


class ImportArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('import', env)
        self.add_flag_one_value('as', '-a', '--as', target='name')
        self.add_anon('module')
        self.add_anon('symbol', default=None)
        self.validate()


class Import(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.module = None
        self.symbol = None
        self.name = None

    def __repr__(self):
        buffer = []
        if self.name:
            buffer.append(f', --as {self.name}')
        buffer.append(f'import({self.module}')
        if self.symbol:
            buffer.append(f', {self.symbol}')
        buffer.append(')')
        return ''.join(buffer)

    # AbstractOp
    
    def setup(self, env):
        wildcard = self.symbol == '*'
        if self.symbol and not (wildcard or self.symbol.isidentifier()):
            raise marcel.exception.KillCommandException(f'symbol must be * or a valid identifier: {self.symbol}')
        if self.name and not self.name.isidentifier():
            raise marcel.exception.KillCommandException(f'name is not a valid identifier: {self.name}')
        if wildcard and self.name is not None:
            raise marcel.exception.KillCommandException(f'Cannot specify --as value when importing *.')

    def run(self, env):
        try:
            env.import_module(self.module, self.symbol, self.name)
        except marcel.exception.ImportException as e:
            raise marcel.exception.KillCommandException(e.message)

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True
