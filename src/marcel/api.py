import marcel.core as _core
import marcel.exception as _exception
import marcel.main as _main

from marcel.op.bash import bash
from marcel.op.cd import cd
from marcel.op.dirs import dirs
from marcel.op.expand import expand
from marcel.op.gen import gen
from marcel.op.head import head
from marcel.op.ls import ls
from marcel.op.map import map
from marcel.op.out import out, Out
from marcel.op.popd import popd
from marcel.op.ps import ps
from marcel.op.pushd import pushd
from marcel.op.pwd import pwd
from marcel.op.red import red
from marcel.op.reverse import reverse
from marcel.op.select import select
from marcel.op.sort import sort
from marcel.op.squish import squish
from marcel.op.sudo import sudo
from marcel.op.tail import tail
from marcel.op.timer import timer
from marcel.op.unique import unique
from marcel.op.version import version
from marcel.op.window import window

MAIN = _main.Main(same_process=True)


class Gather:

    def __init__(self, unwrap_singleton):
        self.unwrap_singleton = unwrap_singleton
        self.output = []

    def append(self, tuple):
        self.output.append(tuple[0] if self.unwrap_singleton and len(tuple) == 1 else tuple)


class Only:

    def __init__(self, unwrap_singleton, pipeline):
        self.unwrap_singleton = unwrap_singleton
        self.pipeline = pipeline
        self.output = None

    def append(self, tuple):
        if self.output is None:
            self.output = tuple[0] if self.unwrap_singleton and len(tuple) == 1 else tuple
        else:
            raise _exception.KillCommandException(f'Pipeline yields multiple rows: {self.pipeline}')


def ensure_pipeline(x):
    if isinstance(x, _core.Pipeline):
        return x
    elif isinstance(x, _core.Op):
        pipeline = _core.Pipeline()
        pipeline.append(x)
    else:
        raise _exception.KillCommandException(f'Not an operator or pipeline: {x}')


def run(x):
    pipeline = ensure_pipeline(x)
    if not isinstance(pipeline.last_op, Out):
        op = out()
        pipeline.append(op)
    MAIN.run_api(pipeline)


def gather(x, unwrap_singleton=True):
    pipeline = ensure_pipeline(x)
    gatherer = Gather(unwrap_singleton)
    pipeline.append(map(lambda *tuple: gatherer.append(tuple)))
    MAIN.run_api(pipeline)
    return gatherer.output


def only(x, unwrap_singleton=True):
    pipeline = ensure_pipeline(x)
    gatherer = Only(unwrap_singleton, pipeline)
    pipeline.append(map(lambda *tuple: gatherer.append(tuple)))
    MAIN.run_api(pipeline)
    return gatherer.output
