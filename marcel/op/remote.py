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
import dill
import subprocess
import sys

import marcel.argsparser
import marcel.core
import marcel.object.error


def remote(env, pipeline):
    assert isinstance(pipeline, marcel.core.Pipelineable)
    pipeline = pipeline.create_pipeline()
    return Remote(env), [pipeline]


class RemoteArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('remote', env)
        self.add_anon('pipeline', convert=self.check_pipeline)
        self.validate()


class Remote(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.host = None
        self.pipeline = None
        self.process = None

    def __repr__(self):
        return f'remote({self.host}, {self.pipeline})'

    # BaseOp

    def setup_1(self):
        self.eval_functions('host')

    def receive(self, _):
        # Start the remote process
        command = ' '.join([
            'ssh',
            '-l',
            self.host.user,
            self.host.addr,
            'farcel.py'
        ])
        self.process = subprocess.Popen(command,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        shell=True,
                                        universal_newlines=False)
        # Pickle the pipeline so that it can be sent to the remote process
        buffer = io.BytesIO()
        pickler = dill.Pickler(buffer)
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
                x = input.load()
                if isinstance(x, marcel.object.error.Error):
                    self.send_error(x)
                else:
                    self.send(x)
        except EOFError as e:
            self.send_complete()

    # Op

    def must_be_first_in_pipeline(self):
        return True

    # Remote

    def set_host(self, host):
        self.host = host
