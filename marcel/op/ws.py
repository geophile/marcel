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
import marcel.object.workspace

Workspace = marcel.object.workspace.Workspace

HELP = '''
{L,wrap=F}ws
{L,wrap=F}ws NAME
{L,wrap=F}ws [-l|--list]
{L,wrap=F}ws [-n|--new] NAME
{L,wrap=F}ws [-o|--open] NAME
{L,wrap=F}ws [-c|--close]
{L,wrap=F}ws [-h|--home] DIR
{L,wrap=F}ws [-d|--delete] NAME
{L,wrap=F}ws [-b|--delete_broken] 
{L,wrap=F}ws [-r|--rename] OLD_NAME NEW_NAME
{L,wrap=F}ws [-2|--copy] NAME COPY_NAME
{L,wrap=F}ws [-e|--export] NAME MWS_FILENAME
{L,wrap=F}ws [-i|--import] MWS_FILENAME NAME

{L,indent=4:28}{r:-l}, {r:--list}              List workspaces.

{L,indent=4:28}{r:-n}, {r:--new}               Create a new workspace with the given NAME.

{L,indent=4:28}{r:-o}, {r:--open}              Open the workspace with the given NAME.

{L,indent=4:28}{r:-c}, {r:--close}             Close the current workspace.

{L,indent=4:28}{r:-h}, {r:--home}              Set the workspace home directory.

{L,indent=4:28}{r:-d}, {r:--delete}            Delete the workspace with the given NAME.

{L,indent=4:28}{r:-b}, {r:--delete-broken}     Delete all broken workspaces.

{L,indent=4:28}{r:-r}, {r:--rename}            Change the name of the workspace named OLD_NAME to NEW_NAME.

{L,indent=4:28}{r:-2}, {r:--copy}              Create a copy of the workspace named NAME, 
under the name COPY_NAME.

{L,indent=4:28}{r:-e}, {r:--export}            Export the workspace with the given NAME 
to the file MWS_FILENAME.

{L,indent=4:28}{r:-i}, {r:--import}            Import file MWS_FILENAME to create a workspace 
with the given NAME.

Provides access to all operations on workspaces.

Without any arguments, {r:ws} writes the current workspace to the output stream.

{r:--list} writes all workspaces to the output stream.

{r:--new} creates a new workspace with the given name.

{r:--open} opens the workspace with the given name. ({r:--open} may be omitted. {r:ws NAME} opens the workspace too.)

{r:--delete} deletes the named workspace. This can only be done while no processes, including the current one,
are not using the workspace.

{r:--delete-broken} deletes all broken workspaces.

{r:--home} sets the workspace's home directory. This can be used to abbreviate the directory printed at the 
marcel prompt.

{r:--rename}, {r:--copy}, {r:--export}, and {r:--import} are not yet
implemented.
'''


def ws(list=False,
       new=None,
       open=None,
       close=False,
       delete=None,
       delete_broken=None,
       home=None,
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
    if delete_broken:
        args.append('--delete-broken')
    if home:
        args.extend(['--home', home])
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
        self.add_flag_no_value('delete_broken', '-b', '--delete-broken')
        self.add_flag_one_value('home', '-h', '--home')
        self.add_flag_one_value('rename', '-r', '--rename')
        self.add_flag_one_value('copy', '-2', '--copy')
        self.add_flag_one_value('export', '-e', '--export', target='exp')
        self.add_flag_one_value('import', '-i', '--import', target='imp')
        self.add_anon('name', default=None)
        self.at_most_one('list', 'new', 'open', 'close', 'delete', 'delete_broken',
                         'home', 'rename', 'copy', 'export', 'import')
        self.validate()


class Ws(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.list = None
        self.new = None
        self.open = None
        self.close = None
        self.delete = None
        self.delete_broken = None
        self.home = None
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
        if self.list:
            self.impl = WsList(self)
        elif self.new is not None:
            self.impl = WsNew(self)
        elif self.open is not None:
            self.impl = WsOpen(self)
        elif self.close:
            self.impl = WsClose(self)
        elif self.delete is not None:
            self.impl = WsDelete(self)
        elif self.delete_broken is not None:
            self.impl = WsDeleteBroken(self)
        elif self.home is not None:
            self.impl = WsHome(self)
        elif self.rename is not None:
            self.impl = WsRename(self)
        elif self.copy is not None:
            self.impl = WsCopy(self)
        elif self.exp is not None:
            self.impl = WsExport(self)
        elif self.imp is not None:
            self.impl = WsImport(self)
        elif self.name is not None:
            self.open = self.name
            self.impl = WsOpen(self)
        else:
            # No args
            self.impl = WsIdentify(self)
        self.impl.setup(env)  # Check that name is given when required

    def run(self, env):
        self.impl.run(env)

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True


class WsImpl(object):

    def __init__(self, op, anon_arg=None):
        self.op = op
        self.anon_arg = anon_arg

    def setup(self, env):
        assert False

    def run(self, env):
        raise marcel.exception.KillCommandException('Not implemented yet')

    # For use by subclasses

    def reconfigure(self, workspace):
        raise marcel.exception.ReconfigureException(workspace)

    def check_anon_arg_absent(self):
        if self.op.name is not None:
            raise marcel.exception.KillCommandException(f'Anonymous argument not allowed.')

    def check_anon_arg_present(self, arg_name):
        if self.anon_arg is None:
            raise marcel.exception.KillCommandException(f'Anonymous argument {arg_name} required.')


class WsIdentify(WsImpl):
    
    def __repr__(self):
        return f'ws(identify)'

    def setup(self, env):
        self.check_anon_arg_absent()

    def run(self, env):
        self.op.send(env, env.workspace)


class WsList(WsImpl):

    def __repr__(self):
        return f'ws(list)'

    def setup(self, env):
        self.check_anon_arg_absent()

    def run(self, env):
        for ws in Workspace.list(env):
            self.op.send(env, ws)


class WsNew(WsImpl):

    def __init__(self, op):
        super().__init__(op, op.new)
    
    def __repr__(self):
        return f'ws(new {self.op.new})'

    def setup(self, env):
        self.check_anon_arg_present('NAME')

    def run(self, env):
        name = self.op.new
        workspace = Workspace(name)
        if workspace.exists(env):
            raise marcel.exception.KillCommandException(f'Workspace {name} already exists.')
        else:
            workspace.create(env)
            workspace.open(env)
            self.op.send(env, workspace)
            self.reconfigure(workspace)


class WsOpen(WsImpl):

    def __init__(self, op):
        super().__init__(op, op.open)

    def __repr__(self):
        return f'ws(open {self.op.open})'

    def setup(self, env):
        self.check_anon_arg_present('NAME')

    def run(self, env):
        name = self.op.open
        workspace = Workspace(name)
        if workspace.exists(env):
            if env.workspace.name != name:
                workspace.open(env)
                self.op.send(env, workspace)
                self.reconfigure(workspace)
                # The workspace will be opened in the handling of the ReconfigurationException
        else:
            raise marcel.exception.KillCommandException(f'There is no workspace named {name}.')


class WsClose(WsImpl):
    
    def __repr__(self):
        return f'ws(close)'

    def setup(self, env):
        self.check_anon_arg_absent()

    def run(self, env):
        workspace = env.workspace
        # DON'T close the workspace. That will happend following the ReconfigureException.
        if not workspace.is_default():
            workspace = Workspace.default()
            workspace.open(env)
            self.op.send(env, workspace)
            self.reconfigure(workspace)


class WsDelete(WsImpl):

    def __init__(self, op):
        super().__init__(op, op.delete)

    def __repr__(self):
        return f'ws(delete {self.op.delete})'

    def setup(self, env):
        self.check_anon_arg_present('NAME')

    def run(self, env):
        name = self.op.delete
        if name == env.workspace.name:
            raise marcel.exception.KillCommandException(
                f'You are using workspace {name}. It cannot be deleted while it is in use.')
        Workspace(name).delete(env)


class WsDeleteBroken(WsImpl):

    def __init__(self, op):
        super().__init__(op)

    def __repr__(self):
        return f'ws(delete-broken {self.op.delete})'

    def setup(self, env):
        self.check_anon_arg_absent()

    def run(self, env):
        Workspace.delete_broken(env)


class WsHome(WsImpl):

    def __init__(self, op):
        super().__init__(op, op.home)

    def __repr__(self):
        return f'ws(home {self.op.home})'

    def setup(self, env):
        self.check_anon_arg_present('DIR')

    def run(self, env):
        workspace = env.workspace
        workspace.set_home(env, self.op.home)
        self.op.send(env, workspace)


class WsRename(WsImpl):

    def __init__(self, op):
        super().__init__(op, op.name)

    def __repr__(self):
        return f'ws(rename {self.op.name} {self.op.name})'

    def setup(self, env):
        self.check_anon_arg_present('NEW_NAME')


class WsCopy(WsImpl):

    def __init__(self, op):
        super().__init__(op, op.name)

    def __repr__(self):
        return f'ws(copy {self.op.copy} {self.op.name})'

    def setup(self, env):
        self.check_anon_arg_present('COPY_NAME')


class WsExport(WsImpl):
    
    def __init__(self, op):
        super().__init__(op, op.name)

    def __repr__(self):
        return f'ws(export {self.op.exp} {self.op.name})'

    def setup(self, env):
        self.check_anon_arg_present('MWS_FILENAME')


class WsImport(WsImpl):
    
    def __init__(self, op):
        super().__init__(op, op.name)

    def __repr__(self):
        return f'ws(import {self.op.imp} {self.op.name})'

    def setup(self, env):
        self.check_anon_arg_present('MWS_FILENAME')
