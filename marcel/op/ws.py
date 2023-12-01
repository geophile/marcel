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
import marcel.object.workspace

Workspace = marcel.object.workspace.Workspace

HELP = '''
{L,wrap=F}ws NAME
{L,wrap=F}ws [-l|--list]
{L,wrap=F}ws [-n|--new] NAME
{L,wrap=F}ws [-o|--open] NAME
{L,wrap=F}ws [-c|--close] 
{L,wrap=F}ws [-d|--delete] NAME
{L,wrap=F}ws [-r|--rename] OLD_NAME NEW_NAME
{L,wrap=F}ws [-2|--copy] NAME COPY_NAME
{L,wrap=F}ws [-e|--export] NAME MWS_FILENAME
{L,wrap=F}ws [-i|--import] MWS_FILENAME NAME

{L,indent=4:28}{r:-l}, {r:--list}              List workspaces.

{L,indent=4:28}{r:-n}, {r:--new}               Create a new workspace_properties with the given NAME.

{L,indent=4:28}{r:-o}, {r:--open}              Open the workspace_properties with the given NAME.

{L,indent=4:28}{r:-c}, {r:--close}             Close the current workspace_properties.

{L,indent=4:28}{r:-d}, {r:--delete}            Delete the workspace_properties with the given NAME.

{L,indent=4:28}{r:-r}, {r:--rename}            Change the name of the workspace_properties named OLD_NAME to NEW_NAME.

{L,indent=4:28}{r:-2}, {r:--copy}              Create a copy of the workspace_properties named NAME, under the name COPY_NAME.

{L,indent=4:28}{r:-e}, {r:--export}            Export the workspace_properties with the given NAME to the file MWS_FILENAME.

{L,indent=4:28}{r:-i}, {r:--import}            Import file MWS_FILENAME to create a workspace_properties with the given NAME.

TBD
'''


def ws(list=False,
       new=None,
       open=None,
       close=False,
       delete=None,
       rename=None,
       copy=None,
       exp=None,
       imp=None,
       name=None):
    args = []
    if list:
        args.append('--list')
    if new:
        args.extend(['--new', new])
    if open:
        args.extend(['--open', open])
    if close:
        args.append('--close')
    if delete:
        args.extend(['--delete', delete])
    if rename:
        args.extend(['--rename', rename])
    if copy:
        args.extend(['--copy', copy])
    if exp:
        args.extend(['--exp', exp])
    if imp:
        args.extend(['--imp', imp])
    if name:
        args.append('name')
    return Ws(), args


class WsArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('ws', env)
        self.add_flag_no_value('list', '-l', '--list')
        self.add_flag_one_value('new', '-n', '--new')
        self.add_flag_one_value('open', '-o', '--open')
        self.add_flag_no_value('close', '-c', '--close')
        self.add_flag_one_value('delete', '-d', '--delete')
        self.add_flag_one_value('rename', '-r', '--rename')
        self.add_flag_one_value('copy', '-2', '--copy')
        self.add_flag_one_value('export', '-e', '--export', target='exp')
        self.add_flag_one_value('import', '-i', '--import', target='imp')
        self.add_anon('name', default=None)
        self.validate()


class Ws(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.list = None
        self.new = None
        self.open = None
        self.close = None
        self.delete = None
        self.rename = None
        self.copy = None
        self.exp = None
        self.imp = None
        self.name = None
        self.impl = None

    def __repr__(self):
        return self.impl.__repr__()

    # AbstractOp

    def setup(self, env):
        if self.list is not None:
            self.impl = WsList(self)
        elif self.new is not None:
            self.impl = WsNew(self)
        elif self.open is not None:
            self.impl = WsOpen(self)
        elif self.close is not None:
            self.impl = WsClose(self)
        elif self.delete is not None:
            self.impl = WsDelete(self)
        elif self.rename is not None:
            self.impl = WsRename(self)
        elif self.copy is not None:
            self.impl = WsCopy(self)
        elif self.exp is not None:
            self.impl = WsExp(self)
        elif self.imp is not None:
            self.impl = WsImp(self)
        elif self.name is not None:
            self.impl = WsOpen(self)
        else:
            raise marcel.argsparser.ArgsError('ws', 'No arguments given.')
        self.impl.setup(env)  # Check that name is given when required

    def run(self, env):
        self.impl.run(env)

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True


class WsImpl(object):

    def __init__(self, op):
        self.op = op

    def setup(self, env):
        assert False

    def run(self, env):
        assert False

    # For use by subclasses

    def check_anon_arg_absent(self):
        if self.op.name is not None:
            raise marcel.exception.KillCommandException(f'Anonymous argument not allowed.')

    def check_anon_arg_present(self, arg_name):
        if self.op.name is not None:
            raise marcel.exception.KillCommandException(f'Anonymous argument not allowed.')


class WsList(WsImpl):
    
    def __repr__(self):
        return f'ws(list)'

    def setup(self, env):
        self.check_anon_arg_absent()

    def run(self, env):
        for wp in Workspace(env).list():
            self.op.send(env, wp)


class WsNew(WsImpl):
    
    def __repr__(self):
        return f'ws(new {self.op.new})'

    def setup(self, env):
        self.check_anon_arg_present('NAME')

    def run(self, env):
        Workspace(env, self.op.new).new()


class WsOpen(WsImpl):
    
    def __repr__(self):
        return f'ws(open {self.op.open})'

    def setup(self, env):
        self.check_anon_arg_present('NAME')

    def run(self, env):
        pass


class WsClose(WsImpl):
    
    def __repr__(self):
        return f'ws(close)'

    def setup(self, env):
        self.check_anon_arg_absent()

    def run(self, env):
        pass


class WsDelete(WsImpl):
    
    def __repr__(self):
        return f'ws(delete {self.op.delete})'

    def setup(self, env):
        self.check_anon_arg_present('NAME')

    def run(self, env):
        pass


class WsRename(WsImpl):
    
    def __repr__(self):
        return f'ws(rename {self.op.rename} {self.op.name})'

    def setup(self, env):
        self.check_anon_arg_present('NEW_NAME')

    def run(self, env):
        pass


class WsCopy(WsImpl):
    
    def __repr__(self):
        return f'ws(copy {self.op.copy} {self.op.name})'

    def setup(self, env):
        self.check_anon_arg_present('COPY_NAME')

    def run(self, env):
        pass


class WsExp(WsImpl):
    
    def __repr__(self):
        return f'ws(export {self.op.exp} {self.op.name})'

    def setup(self, env):
        self.check_anon_arg_present('MWS_FILENAME')

    def run(self, env):
        pass


class WsImp(WsImpl):
    
    def __repr__(self):
        return f'ws(import {self.op.imp} {self.op.name})'

    def setup(self, env):
        self.check_anon_arg_present('MWS_FILENAME')

    def run(self, env):
        pass
