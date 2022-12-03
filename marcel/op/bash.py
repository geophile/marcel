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
import threading

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
        self.args_arg = None
        self.args = None
        self.escape = None
        self.input = None

    def __repr__(self):
        return f'bash(args={self.args_arg})'

    # AbstractOp

    def setup(self):
        self.args = self.eval_function('args_arg')
        self.input = []
        self.escape = (BashShell(self) if len(self.args) == 0 else
                       Interactive(self) if self.env().is_interactive_executable(self.args[0]) else
                       NonInteractive(self))

    def run(self):
        self.receive(None)

    def receive(self, x):
        self.escape.receive(x)

    def flush(self):
        self.escape.flush()
        self.propagate_flush()

    def cleanup(self):
        self.escape.cleanup()


class Escape:

    def __init__(self, op):
        self.op = op

    def __repr__(self):
        return f'{self.__class__.__name__}({self.op})'

    def receive(self, _):
        assert False

    def flush(self):
        pass

    def cleanup(self):
        pass

    def command(self):
        return ' '.join([str(arg) for arg in self.op.args])


class NonInteractive(Escape):

    def __init__(self, op):
        super().__init__(op)
        self.process = None
        self.out_handler = None
        self.err_handler = None
        # There is a race between receive() (from an upstream command's ProcessOutputHandler),
        # and flush(), combing from Command execution.
        self.lock = threading.Lock()

    def receive(self, x):
        self.ensure_command_running()
        if x is not None:
            if len(x) == 1:
                x = x[0]
            self.process.stdin.write(str(x))
            self.process.stdin.write('\n')

    def flush(self):
        self.ensure_command_running()
        self.cleanup()

    def cleanup(self):
        if self.process:
            self.process.stdin.close()
            while self.out_handler.is_alive():
                self.out_handler.join(0.1)
            while self.err_handler.is_alive():
                self.err_handler.join(0.1)
            self.process.stdout.close()
            self.process.stderr.close()
            self.process = None

    def ensure_command_running(self):
        if self.process is None:
            self.lock.acquire()
            if self.process is None:
                command = self.command()
                self.process = subprocess.Popen(command,
                                                shell=True,
                                                executable='/bin/bash',
                                                stdin=subprocess.PIPE,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE,
                                                universal_newlines=True,
                                                preexec_fn=os.setsid)
                self.out_handler = ProcessStdoutHandler(self.process.stdout, self.op)
                self.out_handler.start()
                self.err_handler = ProcessStderrHandler(self.process.stderr, self.op)
                self.err_handler.start()
            self.lock.release()


class Interactive(Escape):

    def __init__(self, op):
        super().__init__(op)
        self.process = subprocess.Popen(self.command(),
                                        shell=True,
                                        executable='/bin/bash',
                                        universal_newlines=True,
                                        preexec_fn=os.setsid)

    def receive(self, _):
        self.process.wait()
        if self.process.returncode != 0:
            marcel.util.print_to_stderr(self.process.stderr, self.op.env())


class BashShell(Escape):

    def __init__(self, op):
        super().__init__(op)
        self.process = subprocess.Popen('bash',
                                        shell=True,
                                        executable='/bin/bash',
                                        universal_newlines=True)

    def receive(self, _):
        self.process.wait()
        if self.process.returncode != 0:
            marcel.util.print_to_stderr(self.process.stderr, self.op.env())


class ProcessOutputHandler(threading.Thread):

    def __init__(self, stream, op):
        super().__init__()
        self.stream = stream
        self.op = op

    def run(self):
        stream = self.stream
        line = stream.readline()
        while len(line) > 0:
            self.send(ProcessOutputHandler.normalize_output(line))
            line = stream.readline()

    def send(self, x):
        assert False

    @staticmethod
    def normalize_output(x):
        x = x.split('\n')
        if len(x[-1]) == 0:
            x = x[:-1]
        return x


class ProcessStdoutHandler(ProcessOutputHandler):

    def __init__(self, stream, op):
        super().__init__(stream, op)

    def __repr__(self):
        return f'ProcessStdoutHandler for {str(self.op)}'

    def send(self, x):
        self.op.send(x)


class ProcessStderrHandler(ProcessOutputHandler):

    def __init__(self, stream, op):
        super().__init__(stream, op)

    def __repr__(self):
        return f'ProcessStderrHandler for {str(self.op)}'

    def send(self, x):
        self.op.send(marcel.object.error.Error(x))
