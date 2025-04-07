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

import os
import subprocess
import threading

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.object.error
import marcel.util

HELP = '''
{L,wrap=F}bash [-i|--interactive] [COMMAND | EXECUTABLE ARG ...]

{L,indent=4:28}{r:-i}, {r:--interactive}       Specifies that the executable to be run 
is interactive. stdin, stdout, and stderr are not handled by marcel.

{L,indent=4:28}COMMAND                 The command to be passed to bash. 

{L,indent=4:28}EXECUTABLE              Host OS executable to be run.
 
{L,indent=4:28}ARG                     Argument to EXECUTABLE

Runs a bash command, which may be given as a single string ({r:COMMAND}), or as a sequence of strings
({r:EXECUTABLE} {r:ARG} ...).

The bash command to be executed can receive stdin from a marcel pipelines, e.g.

{p,indent=4}gen 20 | map (x: (x, x)) | bash "grep 2"

yields:

{p,indent=4,wrap=F}(2, 2)
(12, 12)

{r:gen ... | map ...} yields a stream of tuples {n:(0, 0), ..., (19, 19)}. Piping to 
bash converts these to strings which the bash command can act upon.

Similarly, stdout from the bash command can be piped as strings into marcel operators. For example:

{p,indent=4}bash "cat /etc/passwd" | map (line: line.split(':')[-1]) | unique

The lines of {r:/etc/passwd} are read by the host executable {r:cat}, and the strings are piped into
{r:map ... | unique}. These marcel operators extract the last field of each line, 
(a user's default shell), and removes duplicates. 
'''


# About the use of preexec_fn in Popen:
# See https://pymotw.com/2/subprocess/#process-groups-sessions for more information.


def bash(*bash_args, interactive=False):
    args = ['--interactive'] if interactive else []
    args.extend(bash_args)
    return Bash(), args


class BashArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('bash', env)
        self.add_flag_no_value('interactive', '-i', '--interactive')
        self.add_anon_list('args', convert=self.check_str, target='args_arg')
        self.validate()


class Bash(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.args = None
        self.escape = None
        self.interactive = None
        self.command = None

    def __repr__(self):
        return f'bash({self.command})'

    # AbstractOp

    def setup(self, env):
        def executable(command):
            return ''if command is None or len(command) == 0 else command.split()[0]

        self.args = self.eval_function(env, 'args_arg')
        self.command = ' '.join([str(x).strip() for x in self.args])
        # Try to extract the executable to see if it is interactive.
        interactive = self.interactive or env.is_interactive_executable(executable(self.command))
        self.escape = (BashShell(self) if len(self.command) == 0 else
                       Interactive(self) if interactive else
                       NonInteractive(self))

    def run(self, env):
        self.receive(env, None)

    def receive(self, env, x):
        self.escape.receive(env, x)

    def flush(self, env):
        self.escape.flush(env)
        self.propagate_flush(env)

    def cleanup(self):
        self.escape.cleanup()


class Escape:

    def __init__(self, op):
        self.op = op
        self.bash = marcel.util.bash_executable()

    def __repr__(self):
        return f'{self.__class__.__name__}({self.op})'

    def receive(self, env, _):
        assert False

    def flush(self, env):
        pass

    def cleanup(self):
        pass

    def command(self):
        return self.op.command


class NonInteractive(Escape):

    def __init__(self, op):
        super().__init__(op)
        self.process = None
        self.out_handler = None
        self.err_handler = None
        # There is a race between receive() (from an upstream command's ProcessOutputHandler),
        # and flush(), coming from Command execution.
        self.lock = threading.Lock()

    def receive(self, env, x):
        self.ensure_command_running(env)
        if x is not None:
            if len(x) == 1:
                x = x[0]
            self.process.stdin.write(str(x))
            self.process.stdin.write('\n')

    def flush(self, env):
        self.ensure_command_running(env)
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

    def ensure_command_running(self, env):
        if self.process is None:
            self.lock.acquire()
            if self.process is None:
                command = self.command()
                self.process = subprocess.Popen(command,
                                                shell=True,
                                                executable=self.bash,
                                                stdin=subprocess.PIPE,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE,
                                                universal_newlines=True,
                                                preexec_fn=os.setsid)
                self.out_handler = ProcessStdoutHandler(env, self.process.stdout, self.op)
                self.out_handler.start()
                self.err_handler = ProcessStderrHandler(env, self.process.stderr, self.op)
                self.err_handler.start()
            self.lock.release()


class Interactive(Escape):

    def __init__(self, op):
        super().__init__(op)
        self.process = subprocess.Popen(self.command(),
                                        shell=True,
                                        executable=self.bash,
                                        universal_newlines=True,
                                        preexec_fn=os.setsid)

    def receive(self, env, _):
        self.process.wait()
        if self.process.returncode != 0:
            marcel.util.print_to_stderr(env, self.process.stderr)


class BashShell(Escape):

    def __init__(self, op):
        super().__init__(op)
        self.process = subprocess.Popen('bash',
                                        shell=True,
                                        executable=self.bash,
                                        universal_newlines=True)

    def receive(self, env, _):
        self.process.wait()
        if self.process.returncode != 0:
            marcel.util.print_to_stderr(env, self.process.stderr)


class ProcessOutputHandler(threading.Thread):

    def __init__(self, env, stream, op):
        super().__init__()
        self.env = env
        self.stream = stream
        self.op = op

    def run(self):
        stream = self.stream
        line = stream.readline()
        while len(line) > 0:
            self.send(ProcessOutputHandler.normalize_output(line))
            line = stream.readline()
        self.env = None

    def send(self, x):
        assert False

    @staticmethod
    def normalize_output(x):
        if x[-1] == '\n':
            x = x[:-1]
        return x


class ProcessStdoutHandler(ProcessOutputHandler):

    def __init__(self, env, stream, op):
        super().__init__(env, stream, op)

    def __repr__(self):
        return f'ProcessStdoutHandler for {str(self.op)}'

    def send(self, x):
        self.op.send(self.env, x)


class ProcessStderrHandler(ProcessOutputHandler):

    def __init__(self, env, stream, op):
        super().__init__(env, stream, op)

    def __repr__(self):
        return f'ProcessStderrHandler for {str(self.op)}'

    def send(self, x):
        self.op.send(self.env, marcel.object.error.Error(x))
