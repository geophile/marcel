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

import shlex
import subprocess

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.object.error
import marcel.util


SUMMARY = '''
Run an executable (as opposed to a marcel command). 
'''


DETAILS = '''
It is usually possible to run an executable directly, without using the bash command.
Use this command if the interactive flag is needed.
'''


def bash(env, *args, interactive=False):
    op_args = ['--interactive'] if interactive else []
    op_args.extend(args)
    return Bash(env), op_args


class BashArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('bash', env)
        self.add_flag_no_value('interactive', '-i', '--interactive')
        self.add_anon_list('args', convert=self.check_str)
        self.validate()


class Bash(marcel.core.Op):

    INTERACTIVE_EXECUTABLES = {
        'emacs',
        'less',
        'man',
        'more',
        'psql',
        'top',
        'vi'
    }

    def __init__(self, env):
        super().__init__(env)
        self.interactive = None
        self.args = None
        self.runner = None
        self.input = None

    def __repr__(self):
        return f'bash(args={self.args})'

    # BaseOp

    def setup_1(self):
        self.eval_functions('args')
        self.input = []
        if len(self.args) == 0:
            raise marcel.exception.KillCommandException('No command provided.')
        if self.args[0] in Bash.INTERACTIVE_EXECUTABLES:
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

    BASH_CONTROL = ['>', '<', '>>', '&']

    def __init__(self, op):
        self.op = op

    def run(self):
        assert False

    def command(self):
        return ' '.join([Escape.quote(a) for a in self.op.args])

    # The use of looks_globby is a hack due to bug 38. Quoting of a glob prevents glob
    # expansion. So this is definitely wrong sometimes, but I'm not sure what else to do.
    # This is trading a pretty blatant bug for a much more obscure one.
    # TODO: It looks like quoting everything except the glob characters might work.e g.
    # TODO: "/var/log/syslog"*. Haven't played with this enough to conclude it is a complete fix.
    @staticmethod
    def quote(x):
        return x if x in Escape.BASH_CONTROL or Escape.looks_globby(x) else shlex.quote(x)

    @staticmethod
    def looks_globby(x):
        return '*' in x or '?' in x or '[' in x


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
                                   universal_newlines=True)
        input = NonInteractive.to_string(self.op.input)
        stdout, stderr = process.communicate(input=input)
        process.wait()
        # stdout
        op = self.op
        for line in NonInteractive.normalize_output(stdout):
            op.send(line)
        # stderr
        for line in NonInteractive.normalize_output(stderr):
            op.send_error(marcel.object.error.Error(line))

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
                                   universal_newlines=True)
        process.wait()
        if process.returncode != 0:
            print(f'Escaped command failed with exit code {process.returncode}: {" ".join(self.op.args)}')
            marcel.util.print_to_stderr(process.stderr, self.op.env())
1
