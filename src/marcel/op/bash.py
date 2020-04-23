import argparse
import shlex
import subprocess
import sys

import marcel.core
import marcel.object.error


SUMMARY = '''
Run an executable (as opposed to a marcel command). 
'''


DETAILS = '''
It is usually possible to run an executable directly, without using the bash command.
Use this command if  the interactive flag is needed.
'''


def bash():
    return Bash()


class BashArgParser(marcel.core.ArgParser):

    def __init__(self, global_state):
        super().__init__('bash', global_state, None, SUMMARY, DETAILS)
        self.add_argument('-i', '--interactive',
                          action='store_true',
                          help='The command is run interactively. stdin, stdout, and stderr are ignored.')
        self.add_argument('args',
                          nargs=argparse.REMAINDER,
                          help='''These arguments comprise a command that can be executed by a Linux
                          bash shell.''')


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

    def __init__(self):
        super().__init__()
        self.interactive = None
        self.args = None
        self.runner = None
        self.input = []

    def __repr__(self):
        return f'bash(args={self.args})'

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup_1(self):
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
            op.send(marcel.object.error.Error(line))

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
            print(process.stderr, file=sys.stderr)
1
