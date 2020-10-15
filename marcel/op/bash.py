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

import os
import subprocess

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.object.error
import marcel.util

HELP = '''
{L,wrap=F}bash [-i|--interactive] ARG ...

{L,indent=4:28}{r:-i}, {r:--interactive}       Specifies that the executable to be run 
is interactive. stdin, stdout, and stderr are not handled by marcel. 

Runs the executable specified by the first {r:ARG}, (as opposed to a marcel command).
Remaining {r:ARG}s are arguments to the executable. 

It is usually possible to run an executable directly, without using the bash command.
Use this command if the {r:--interactive} flag is needed.
'''


# About the use of preexec_fn in Popen:
# See https://pymotw.com/2/subprocess/#process-groups-sessions for more information.


def bash(env, *args, interactive=False):
    op_args = ['--interactive'] if interactive else []
    op_args.extend(args)
    return Bash(env), op_args


class BashArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('bash', env)
        self.add_flag_no_value('interactive', '-i', '--interactive')
        self.add_anon_list('args', convert=self.check_str, target='args_arg')
        self.validate()


class Bash(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.interactive = None
        self.args_arg = None
        self.args = None
        self.runner = None
        self.input = None

    def __repr__(self):
        return f'bash(args={self.args})'

    # AbstractOp

    def setup(self):
        self.args = self.eval_function('args_arg')
        self.input = []
        if len(self.args) == 0:
            self.runner = BashShell(self)
        else:
            if self.args[0] in self.env().getvar('INTERACTIVE_EXECUTABLES'):
                self.interactive = True
            self.runner = Interactive(self) if self.interactive else NonInteractive(self)

    def receive(self, x):
        if x is not None:
            if len(x) == 1:
                x = x[0]
            self.input.append(str(x))

    def receive_complete(self):
        self.runner.run()
        self.send_complete()


class Escape:

    def __init__(self, op):
        self.op = op

    def run(self):
        assert False

    def command(self):
        return ' '.join([str(arg) for arg in self.op.args])


class NonInteractive(Escape):

    def __init__(self, op):
        super().__init__(op)

    def run(self):
        process = subprocess.Popen(self.command(),
                                   shell=True,
                                   executable='/bin/bash',
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   universal_newlines=True,
                                   preexec_fn=os.setsid)
        input = NonInteractive.to_string(self.op.input)
        try:
            stdout, stderr = process.communicate(input=input)
        except Exception as e:
            self.op.fatal_error(None, f'Caught {e.__class__.__name__}')
        # stdout
        op = self.op
        for line in NonInteractive.normalize_output(stdout):
            op.send(line)
        # stderr
        for line in NonInteractive.normalize_output(stderr):
            op.non_fatal_error(error=marcel.object.error.Error(line))

    @staticmethod
    def normalize_output(x):
        x = x.split('\n')
        if len(x[-1]) == 0:
            x = x[:-1]
        return x

    @staticmethod
    def to_string(input):
        return '\n'.join(input)


class Interactive(Escape):

    def __init__(self, op):
        super().__init__(op)

    def run(self):
        process = subprocess.Popen(self.command(),
                                   shell=True,
                                   executable='/bin/bash',
                                   universal_newlines=True,
                                   preexec_fn=os.setsid)
        process.wait()
        if process.returncode != 0:
            print(f'Escaped command failed with exit code {process.returncode}: {" ".join(self.op.args)}')
            marcel.util.print_to_stderr(process.stderr, self.op.env())


class BashShell(Escape):

    def __init__(self, op):
        super().__init__(op)

    def run(self):
        process = subprocess.Popen('bash',
                                   shell=True,
                                   executable='/bin/bash',
                                   universal_newlines=True)
        process.wait()
        if process.returncode != 0:
            print(f'Escaped command failed with exit code {process.returncode}: {" ".join(self.op.args)}')
            marcel.util.print_to_stderr(process.stderr, self.op.env())
