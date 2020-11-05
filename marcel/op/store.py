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
import marcel.picklefile
import marcel.reservoir

HELP = '''
{L,wrap=F}store [-a|--append] TARGET
{L,wrap=F}> TARGET
{L,wrap=F}>> TARGET

{L,indent=4:28}{r:-a}, {r:--append}            Append to {r:TARGET}s list, instead of replacing.

{L,indent=4:28}{r:TARGET}                  An environment variable or a file.

Write the incoming tuples to the {r:TARGET}. 

A {r:TARGET} is either an environment variable
or a file. A variable is indicated by a Python identifier, and any other string identifies a file.
(So {n:abc} is an identifier, while {n:./abc} is a file in the current directory.) 

By default, the current value of {r:TARGET} is replaced. 
If {r:--append} is specified, then the incoming tuples are appended. (And,
in case the {r:TARGET} is an environment variable, that the variable's value must have previously
been assigned tuples from a stream.)

There is special syntax for the {r:store} operator: {r:store TARGET} can be written as {r:> TARGET}. 
With this alternative syntax, the {r:>} acts as a pipe ({r:|}). So, for example, the following command:

{L,wrap=F}gen 5 | store x

stores the stream carrying {r:0, 1, 2, 3, 4} in variable {r:x}. This can also be written as:

{L,wrap=F}gen 5 > x

The symbol {r:>>} is used to append to the contents of the {r:TARGET}, instead of
replacing the value, e.g. {r:gen 5 >> x}. 
'''


def store(env, target, append=False):
    """
    Store the environment.

    Args:
        env: (todo): write your description
        target: (str): write your description
        append: (todo): write your description
    """
    store = Store(env)
    args = []
    if append:
        args.append('--append')
    if type(target) in (str, marcel.reservoir.Reservoir):
        args.append(target)
    else:
        raise marcel.exception.KillCommandException(f'{target} is not a Reservoir: {type(target)}')
    return store, args


class StoreArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        """
        Initialize the env.

        Args:
            self: (todo): write your description
            env: (todo): write your description
        """
        super().__init__('store', env)
        self.add_flag_no_value('append', '-a', '--append')
        # init_target actually creates the target file or reservoir if it doesn't exist. This would 
        # normally be done by setup. However, for commands that don't terminate for a while, (e.g. ls -r / > x),
        # we want the variable available immediately. This allows the long-running command to be run in background,
        # monitoring progress, e.g. x > tail 5.
        self.add_anon('target', convert=self.init_target)
        self.validate()


class Store(marcel.core.Op):

    def __init__(self, env):
        """
        Initialize the environment.

        Args:
            self: (todo): write your description
            env: (todo): write your description
        """
        super().__init__(env)
        self.target = None
        self.append = None
        self.picklefile = None
        self.writer = None
        self.nesting = None

    def __repr__(self):
        """
        Return a repr representation of this field.

        Args:
            self: (todo): write your description
        """
        return f'store({self.target}, append)' if self.append else f'store({self.target})'

    # AbstractOp

    def setup(self):
        """
        Sets up the target.

        Args:
            self: (todo): write your description
        """
        if type(self.target) is marcel.reservoir.Reservoir:
            # API
            self.picklefile = self.target
        elif type(self.target) is str:
            # API: string is a filename.
            # Interactive: string is a filename or environment variable name.
            if self.target.isidentifier():
                self.picklefile = self.getvar(self.target)
                if self.append and type(self.picklefile) is not marcel.reservoir.Reservoir:
                    raise marcel.exception.KillCommandException(
                        f'{self.target} is not usable as a reservoir, it stores a value of type {type(self.picklefile)}.')
                self.env().mark_possibly_changed(self.target)
            else:
                self.picklefile = marcel.picklefile.PickleFile(self.target)
        elif self.target is None:
            raise marcel.exception.KillCommandException(f'Reservoir is undefined.')
        else:
            raise marcel.exception.KillCommandException(
                f'{self.target} is not usable as a reservoir, it stores a value of type {type(self.picklefile)}.')
        self.writer = self.picklefile.writer(self.append)
        self.nesting = self.env().vars().n_scopes()

    def receive(self, x):
        """
        Receive the stream.

        Args:
            self: (todo): write your description
            x: (todo): write your description
        """
        try:
            self.writer.write(x)
        except:
            self.writer.close()
            raise

    def receive_complete(self):
        """
        Receive a complete message.

        Args:
            self: (todo): write your description
        """
        # self.nesting, and the conditional execution of close() fixes bug 126. receive_complete for an op
        # can sometimes be reached on multiple paths, e.g.
        #         fact = [x: gen (x) 1 | args [n: gen (n) 1 | red * | map (f: (n, f))]]
        #         fact (100) > f
        # "> f" gives rise to store(f) on the pipeline to be executed (fact (100) > f). But store's receive_complete
        # is reached on execution of the fact pipeline, due to the way that Op receivers are connected. We only
        # want to actually close self.writer in the pipeline that created it.
        if self.env().vars().n_scopes() == self.nesting:
            self.writer.close()
        self.send_complete()


