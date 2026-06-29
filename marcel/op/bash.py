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
import selectors
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

The bash command to be executed can receive stdin from a marcel pipeline, e.g.

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


def dump(x):
    print(f'{threading.current_thread().name}: {x}', flush=True)

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
        self.escape.run(env)

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

    def run(self, env):
        self.receive(env, None)

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
        self.output_handler = None
        self.lock = threading.Lock()

    def receive(self, env, x):
        self.ensure_command_running(env)
        if x is not None:
            if len(x) == 1:
                x = x[0]
            self.process.stdin.write(str(x))
            self.process.stdin.write('\n')
            self.process.stdin.flush()

    def flush(self, env):
        self.process.stdin.close()
        self.output_handler.join()

    def cleanup(self):
        self.shutdown()

    # Implementation

    def ensure_command_running(self, env):
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
            self.output_handler = ProcessOutputHandler(env, self)
            self.output_handler.start()

    def shutdown(self):
        while self.output_handler.is_alive():
            self.output_handler.join(0.1)
        self.lock.acquire()
        try:
            if self.process:
                self.process.wait()
                self.process.stdout.close()
                self.process.stderr.close()
                self.process = None
        finally:
            self.lock.release()


class Interactive(Escape):

    def __init__(self, op):
        super().__init__(op)
        self.process = subprocess.Popen(self.command(),
                                        shell=True,
                                        executable=self.bash,
                                        universal_newlines=True,
                                        preexec_fn=os.setsid)

    def run(self, env):
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

    def __init__(self, env, owner):
        super().__init__()
        self.env = env
        self.owner = owner

    def run(self):
        process = self.owner.process
        op = self.owner.op
        lock = self.owner.lock
        sel = selectors.DefaultSelector()
        sel.register(process.stdout, selectors.EVENT_READ)
        sel.register(process.stderr, selectors.EVENT_READ)
        while True:
            events = sel.select(timeout=0.1)
            lock.acquire()
            try:
                if not events and process.poll() is not None:
                    break
                for key, _ in events:
                    stream = key.fileobj
                    line = stream.readline()
                    if not line:
                        sel.unregister(key.fileobj)
                    else:
                        output = ProcessOutputHandler.normalize_output(line)
                        if stream is process.stdout:
                            op.send(self.env, output)
                        elif stream is process.stderr:
                            op.send(self.env, marcel.object.error.Error(output))
            finally:
                lock.release()
        process.wait()

    @staticmethod
    def normalize_output(x):
        if x[-1] == '\n':
            x = x[:-1]
        return x
