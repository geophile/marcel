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

import io
import subprocess
import sys

import dill

import marcel.argsparser
import marcel.core
import marcel.exception


HELP = '''
{L,wrap=F}sudo FLAGS PIPELINE

{L,indent=4:28}{r:FLAGS}                   Flags to the host OS sudo command.
{L,indent=4:28}{r:PIPELINE}                Command to be executed under control of sudo

For example, running this command (assuming you are not root), would result in "Permission denied":

{L,wrap=F}ls /root

Running the command via {r:sudo} would work:

{L,wrap=F}sudo [ ls /root ]
'''


def sudo(env, pipeline, *args):
    args = list(args)
    args.append(pipeline.create_pipeline())
    return Sudo(env), args


# The sudo command has 0 or more flags and arguments for the native sudo command, followed by a pipeline.
# There are a lot of flags, and it might not be a great idea to model them all. How much do those flags
# differ across distros? And since the flags aren't being modeled by the arg parser, we can't say that the
# last arg is, specifically, a pipeline. So just get all the args, and assume the last one is a pipeline.
# This means that setup has to convert the pipeline ref to a pipeline.
class SudoArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('sudo', env)
        self.add_anon_list('args', convert=self.check_str_and_pipeline)
        self.validate()

    def check_str_and_pipeline(self, arg, x):
        # This isn't really accurate. The last arg must be a pipeline. The preceding ones must be str.
        if type(x) not in (str, marcel.core.Pipeline):
            raise marcel.argsparser.ArgsError(self.op_name,
                                              f'Arguments must be strings (flags to sudo) followed by a pipeline: {x}')
        return x


class Sudo(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.args = None
        self.pipeline = None

    def __repr__(self):
        return f'sudo({self.pipeline})'

    # AbstractOp

    def setup(self):
        if len(self.args) == 0:
            raise marcel.exception.KillCommandException('Missing pipeline')
        self.pipeline = self.args.pop()
        if not isinstance(self.pipeline, marcel.core.Pipeline):
            raise marcel.exception.KillCommandException('Last argument to sudo must be a pipeline')

    def set_env(self, env):
        super().set_env(env)
        self.pipeline.set_env(env)

    # Op

    def receive(self, _):
        # Start the remote process
        command = ' '.join(['sudo'] + self.args + ['farcel.py'])
        self.process = subprocess.Popen(command,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        shell=True,
                                        universal_newlines=False)
        # The pipeline's environment will be set remotely.
        # Send the environment and pipeline
        buffer = io.BytesIO()
        pickler = dill.Pickler(buffer)
        pickler.dump(self.env())
        pickler.dump(self.pipeline)
        buffer.seek(0)
        stdout, stderr = self.process.communicate(input=buffer.getvalue())
        # Wait for completion (already guaranteed by communicate returning?)
        self.process.wait()
        # Handle results
        stderr_lines = stderr.decode('utf-8').split('\n')
        if len(stderr_lines[-1]) == 0:
            del stderr_lines[-1]
        sys.stdout.flush()
        for line in stderr_lines:
            print(line, file=sys.stderr)
        sys.stderr.flush()
        input = dill.Unpickler(io.BytesIO(stdout))
        try:
            while True:
                self.send(input.load())
        except EOFError:
            self.send_complete()

    # Op

    def must_be_first_in_pipeline(self):
        return True
