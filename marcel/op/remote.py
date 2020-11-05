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
import os
import subprocess
import sys

import dill

import marcel.argsparser
import marcel.core
import marcel.object.error
import marcel.util


def remote(env, pipeline):
    """
    Create a new pipeline.

    Args:
        env: (todo): write your description
        pipeline: (todo): write your description
    """
    assert isinstance(pipeline, marcel.core.Pipelineable)
    pipeline = pipeline.create_pipeline()
    return Remote(env), [pipeline]


class RemoteArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        """
        Initialize the environment.

        Args:
            self: (todo): write your description
            env: (todo): write your description
        """
        super().__init__('remote', env)
        self.add_anon('pipeline', convert=self.check_pipeline)
        self.validate()


class Remote(marcel.core.Op):

    def __init__(self, env):
        """
        Initialize the pipeline.

        Args:
            self: (todo): write your description
            env: (todo): write your description
        """
        super().__init__(env)
        self.host = None
        self.pipeline = None
        self.process = None

    def __repr__(self):
        """
        Return a repr representation of a repr__.

        Args:
            self: (todo): write your description
        """
        return f'remote({self.host}, {self.pipeline})'

    # AbstractOp

    def setup(self):
        """
        Sets the host.

        Args:
            self: (todo): write your description
        """
        self.host = self.eval_function('host', str)

    def receive(self, _):
        """
        Receive data from the socket.

        Args:
            self: (todo): write your description
            _: (todo): write your description
        """
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
        buffer = io.BytesIO()
        pickler = dill.Pickler(buffer)
        pickler.dump(self.env().remotify())
        pickler.dump(self.pipeline)
        buffer.seek(0)
        try:
            stdout, stderr = self.process.communicate(input=buffer.getvalue())
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
        except BaseException as e:
            marcel.util.print_stack()
            print(e)

    # Op

    def must_be_first_in_pipeline(self):
        """
        Returns true if the pipeline is in the pipeline.

        Args:
            self: (todo): write your description
        """
        return True

    # Remote

    def set_host(self, host):
        """
        Set the host s host.

        Args:
            self: (todo): write your description
            host: (str): write your description
        """
        self.host = host
