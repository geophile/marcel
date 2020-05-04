import sys as _sys

import marcel.core as _core
import marcel.exception as _exception
import marcel.main as _main
import marcel.object.color as _color
import marcel.util as _util

from marcel.op.bash import bash
from marcel.op.cd import cd
from marcel.op.dirs import dirs
from marcel.op.expand import expand
from marcel.op.gen import gen
from marcel.op.head import head
from marcel.op.ls import ls
from marcel.op.map import map
from marcel.op.out import out, Out as _Out
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

from marcel.op.gather import gather as _gather

_MAIN = _main.Main(same_process=True)
# No colors for API
_MAIN.env.set_color_scheme(_color.ColorScheme())


def _default_error_handler(env, error):
    print(error.render_full(env.color_scheme()), file=_sys.stderr)


def _noop_error_handler(env, error):
    pass


# Create a pipeline, by copying if necessary. The caller is going to append an op, and we
# don't want to modify the original.
def _prepare_pipeline(x):
    if isinstance(x, _core.Pipeline):
        pipeline = _util.clone(x)
    elif isinstance(x, _core.Op):
        pipeline = _core.Pipeline()
        pipeline.append(x)
    else:
        raise _exception.KillCommandException(f'Not an operator or pipeline: {x}')
    pipeline.set_env(_MAIN.env)
    return pipeline


def run(x):
    pipeline = _prepare_pipeline(x)
    pipeline.set_error_handler(_default_error_handler)
    if not isinstance(pipeline.last_op, _Out):
        op = out()
        pipeline.append(op)
    _MAIN.run_api(pipeline)


def gather(x, unwrap_singleton=True, errors=None, error_handler=None):
    if errors is not None and error_handler is not None:
        raise _exception.KillCommandException(f'Cannot specify both errors and error_handler')
    output = []
    pipeline = _prepare_pipeline(x)
    pipeline.set_error_handler(_noop_error_handler)
    terminal_op = _gather(unwrap_singleton, output, errors=errors, error_handler=error_handler)
    pipeline.append(terminal_op)
    _MAIN.run_api(pipeline)
    return output


def first(x, unwrap_singleton=True, errors=None, error_handler=None):
    if errors is not None and error_handler is not None:
        raise _exception.KillCommandException(f'Cannot specify both errors and error_handler')
    output = []
    pipeline = _prepare_pipeline(x)
    pipeline.set_error_handler(_noop_error_handler)
    terminal_op = _gather(unwrap_singleton, output, errors=errors, error_handler=error_handler, stop_after_first=True)
    pipeline.append(terminal_op)
    try:
        _MAIN.run_api(pipeline)
    except _exception.KillCommandAfterFirstException:
        pass
    return None if len(output) == 0 else output[0]
