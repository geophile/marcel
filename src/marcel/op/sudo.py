import argparse
import io
import pickle
import subprocess
import sys

import marcel.core


def sudo():
    return Sudo()

# The sudo command has 0 or more flags and arguments for the native sudo command, followed by a pipeline.
# There are a lot of flags, and it might not be a great idea to model them all. How much do those flags
# differ across distros? And since the flags aren't being modeled by the arg parser, we can't say that the
# last arg is, specifically, a pipeline. So just get all the args, and assume the last one is a pipeline.
# This means that setup_1 has to convert the pipeline ref to a pipeline.


class SudoArgParser(marcel.core.ArgParser):

    def __init__(self, global_state):
        super().__init__('sudo', global_state)
        self.add_argument('args', nargs=argparse.REMAINDER)

    # Insert -- as first arg to cause parse_args to treat all sudo args as positional.
    def parse_args(self, args=None, namespace=None):
        if args is not None:
            args = ['--'] + args
        super().parse_args(args, namespace)


class Sudo(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.args = None
        self.pipeline = None

    def __repr__(self):
        return f'sudo({self.pipeline})'

    # BaseOp

    def setup_1(self):
        # Now the -- arg has to be removed
        assert self.args[0] == '--'
        self.args = self.args[1:]
        if len(self.args) == 0:
            raise marcel.exception.KillCommandException('Missing pipeline')
        pipeline_ref = self.args.pop()
        self.pipeline = self.referenced_pipeline(pipeline_ref)
        if not isinstance(self.pipeline, marcel.core.Pipeline):
            raise marcel.exception.KillCommandException('Last argument to sudo must be a pipeline')

    def receive(self, _):
        # Start the remote process
        # TODO: shlex.quote args, as in bash.Escape
        command = ' '.join(['sudo'] + self.args + ['farcel.py'])
        self.process = subprocess.Popen(command,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        shell=True,
                                        universal_newlines=False)
        # Pickle the pipeline so that it can be sent to the remote process
        buffer = io.BytesIO()
        pickler = pickle.Pickler(buffer)
        pickler.dump(self.pipeline)
        buffer.seek(0)
        stdout, stderr = self.process.communicate(input=buffer.getvalue())
        # Wait for completion (already guaranteed by communicate returning?)
        self.process.wait()
        # Handle results
        stderr_lines = stderr.decode('utf-8').split('\n')
        if len(stderr_lines[-1]) == 0:
            del stderr_lines[-1]
        for line in stderr_lines:
            print(line, file=sys.stderr)
        input = pickle.Unpickler(io.BytesIO(stdout))
        try:
            while True:
                self.send(input.load())
        except EOFError:
            self.send_complete()

    # Op

    def must_be_first_in_pipeline(self):
        return True
