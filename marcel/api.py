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

import marcel.core as _core
import marcel.exception as _exception
import marcel.main as _main
import marcel.object.error as _error

from marcel.op.bash import bash as _bash
from marcel.op.cd import cd as _cd
from marcel.op.dirs import dirs as _dirs
from marcel.op.expand import expand as _expand
from marcel.op.first import _first
from marcel.op.fork import fork as _fork
from marcel.op.gather import _gather
from marcel.op.gen import gen as _gen
from marcel.op.head import head as _head
from marcel.op.join import join as _join
from marcel.op.ls import ls as _ls
from marcel.op.map import map as _map
from marcel.op.out import out as _out, Out as _Out
from marcel.op.popd import popd as _popd
from marcel.op.ps import ps as _ps
from marcel.op.pushd import pushd as _pushd
from marcel.op.pwd import pwd as _pwd
from marcel.op.red import red as _red
from marcel.op.remote import remote as _remote
from marcel.op.reverse import reverse as _reverse
from marcel.op.select import select as _select
from marcel.op.sort import sort as _sort
from marcel.op.squish import squish as _squish
from marcel.op.sudo import sudo as _sudo
from marcel.op.tail import tail as _tail
from marcel.op.timer import timer as _timer
from marcel.op.unique import unique as _unique
from marcel.op.version import version as _version
from marcel.op.window import window as _window
from marcel.builtin import *
from marcel.reduction import *

_MAIN = _main.Main(same_process=True)
# No colors for API
_MAIN.env.set_color_scheme(None)


def bash(*args, **kwargs): return _generate_op(_bash, *args, **kwargs)
def cd(*args, **kwargs): return _generate_op(_cd, *args, **kwargs)
def dirs(*args, **kwargs): return _generate_op(_dirs, *args, **kwargs)
def expand(*args, **kwargs): return _generate_op(_expand, *args, **kwargs)
def fork(*args, **kwargs): return _generate_op(_fork, *args, **kwargs)
def gen(*args, **kwargs): return _generate_op(_gen, *args, **kwargs)
def head(*args, **kwargs): return _generate_op(_head, *args, **kwargs)
def join(*args, **kwargs): return _generate_op(_join, *args, **kwargs)
def ls(*args, **kwargs): return _generate_op(_ls, *args, **kwargs)
def map(*args, **kwargs): return _generate_op(_map, *args, **kwargs)
def out(*args, **kwargs): return _generate_op(_out, *args, **kwargs)
def popd(*args, **kwargs): return _generate_op(_popd, *args, **kwargs)
def ps(*args, **kwargs): return _generate_op(_ps, *args, **kwargs)
def pushd(*args, **kwargs): return _generate_op(_pushd, *args, **kwargs)
def pwd(*args, **kwargs): return _generate_op(_pwd, *args, **kwargs)
def red(*args, **kwargs): return _generate_op(_red, *args, **kwargs)
def reverse(*args, **kwargs): return _generate_op(_reverse, *args, **kwargs)
def select(*args, **kwargs): return _generate_op(_select, *args, **kwargs)
def sort(*args, **kwargs): return _generate_op(_sort, *args, **kwargs)
def squish(*args, **kwargs): return _generate_op(_squish, *args, **kwargs)
def sudo(*args, **kwargs): return _generate_op(_sudo, *args, **kwargs)
def tail(*args, **kwargs): return _generate_op(_tail, *args, **kwargs)
def timer(*args, **kwargs): return _generate_op(_timer, *args, **kwargs)
def unique(*args, **kwargs): return _generate_op(_unique, *args, **kwargs)
def version(*args, **kwargs): return _generate_op(_version, *args, **kwargs)
def window(*args, **kwargs): return _generate_op(_window, *args, **kwargs)


remote = fork


# Utilities

def _generate_op(f, *args, **kwargs):
    op, arglist = f(_MAIN.env, *args, **kwargs)
    _MAIN.op_modules[op.op_name()].args_parser().parse(arglist, op)
    return op


def _default_error_handler(env, error):
    print(error.render_full(env.color_scheme()))


def _noop_error_handler(env, error):
    pass


# Create a pipeline, by copying if necessary. The caller is going to append an op, and we
# don't want to modify the original.
def _prepare_pipeline(x):
    assert isinstance(x, _core.Pipelineable)
    return x.create_pipeline()


def run(x):
    pipeline = _prepare_pipeline(x)
    if not isinstance(pipeline.last_op, _Out):
        pipeline.append(out())
    pipeline.set_error_handler(_default_error_handler)
    _MAIN.run_api(pipeline)


def gather(x, unwrap_singleton=True, errors=None, error_handler=None):
    pipeline = _prepare_pipeline(x)
    output = []
    terminal_op = _gather(_MAIN.env,
                          output=output,
                          unwrap_singleton=unwrap_singleton,
                          errors=errors,
                          error_handler=error_handler)
    pipeline.append(terminal_op)
    pipeline.set_error_handler(_noop_error_handler)
    _MAIN.run_api(pipeline)
    return output


def first(x, unwrap_singleton=True, errors=None, error_handler=None):
    pipeline = _prepare_pipeline(x)
    output = []
    terminal_op = _first(_MAIN.env,
                         output=output,
                         unwrap_singleton=unwrap_singleton,
                         errors=errors,
                         error_handler=error_handler)
    pipeline.append(terminal_op)
    pipeline.set_error_handler(_noop_error_handler)
    try:
        _MAIN.run_api(pipeline)
    except _exception.StopAfterFirst:
        pass
    first = None if len(output) == 0 else output[0]
    if isinstance(first, _error.Error):
        raise Exception(first)
    return first
