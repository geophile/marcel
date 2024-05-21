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

import atexit
import os as _os
import pathlib as _pathlib
import tempfile

import marcel.core as _core
import marcel.env as _env_  # _env would create a name conflict with import of marcel.op.env below
import marcel.exception as _exception
import marcel.main as _main
import marcel.object.error as _error
import marcel.opmodule
import marcel.reservoir as _reservoir
import marcel.structish
import marcel.util

from marcel.op.args import args as _args
from marcel.op.assign import assign as _assign
from marcel.op.bash import bash as _bash
from marcel.op.case import case as _case
from marcel.op.cast import cast as _cast
from marcel.op.cd import cd as _cd
from marcel.op.difference import difference as _difference
from marcel.op.dirs import dirs as _dirs
from marcel.op.download import download as _download
from marcel.op.env import env as _env
from marcel.op.expand import expand as _expand
from marcel.op.filter import filt as _filt
from marcel.op.first import _first
from marcel.op.fork import fork as _fork
from marcel.op.gather import _gather
from marcel.op.gen import gen as _gen
from marcel.op.head import head as _head
from marcel.op.ifelse import ifelse as _ifelse
from marcel.op.ifthen import ifthen as _ifthen
from marcel.op.intersect import intersect as _intersect
from marcel.op.join import join as _join
from marcel.op.load import load as _load
from marcel.op.ls import ls as _ls
from marcel.op.map import map as _map
from marcel.op.popd import popd as _popd
from marcel.op.ps import ps as _ps
from marcel.op.pushd import pushd as _pushd
from marcel.op.pwd import pwd as _pwd
from marcel.op.read import read as _read
from marcel.op.red import red as _red
from marcel.op.remote import remote as _remote
from marcel.op.reverse import reverse as _reverse
from marcel.op.select import select as _select
from marcel.op.sort import sort as _sort
from marcel.op.sql import sql as _sql
from marcel.op.squish import squish as _squish
from marcel.op.store import store as _store
from marcel.op.sudo import sudo as _sudo
from marcel.op.tail import tail as _tail
from marcel.op.tee import tee as _tee
from marcel.op.timer import timer as _timer
from marcel.op.unique import unique as _unique
from marcel.op.union import union as _union
from marcel.op.upload import upload as _upload
from marcel.op.version import version as _version
from marcel.op.window import window as _window
from marcel.op.write import write as _write, Write as _Write
from marcel.builtin import *
from marcel.reduction import *


class _ShutdownHook(object):

    def __init__(self):
        self.registered = False

    def ensure_registered(self):
        if not self.registered:
            atexit.register(_ShutdownHook.shutdown)
            self.registered = True

    @staticmethod
    def shutdown():
        for reservoir in _RESERVOIRS:
            reservoir.ensure_deleted()


_RESERVOIRS = []
PWD = None
DIRS = [_pathlib.Path(_os.getcwd())]
DB_DEFAULT = None
_ENV = _env_.EnvironmentAPI.create(globals())
_MAIN = _main.MainAPI(_ENV)
SHUTDOWN_HOOK = _ShutdownHook()




def args(*args, **kwargs): return _generate_op(_args, *args, **kwargs)


def assign(*args, **kwargs): return _generate_op(_assign, *args, **kwargs)


def bash(*args, **kwargs): return _generate_op(_bash, *args, **kwargs)


def case(*args, **kwargs): return _generate_op(_case, *args, **kwargs)


def cast(*args, **kwargs): return _generate_op(_cast, *args, **kwargs)


def cd(*args, **kwargs): return _generate_op(_cd, *args, **kwargs)


def difference(*args, **kwargs): return _generate_op(_difference, *args, **kwargs)


def dirs(*args, **kwargs): return _generate_op(_dirs, *args, **kwargs)


def download(*args, **kwargs): return _generate_op(_download, *args, **kwargs)


def env(*args, **kwargs): return _generate_op(_env, *args, **kwargs)


def expand(*args, **kwargs): return _generate_op(_expand, *args, **kwargs)


def filt(*args, **kwargs): return _generate_op(_filt, *args, **kwargs)


def fork(*args, **kwargs): return _generate_op(_fork, *args, **kwargs)


def gen(*args, **kwargs): return _generate_op(_gen, *args, **kwargs)


def head(*args, **kwargs): return _generate_op(_head, *args, **kwargs)


def ifelse(*args, **kwargs): return _generate_op(_ifelse, *args, **kwargs)


def ifthen(*args, **kwargs): return _generate_op(_ifthen, *args, **kwargs)


def intersect(*args, **kwargs): return _generate_op(_intersect, *args, **kwargs)


def join(*args, **kwargs): return _generate_op(_join, *args, **kwargs)


def load(*args, **kwargs): return _generate_op(_load, *args, **kwargs)


def ls(*args, **kwargs): return _generate_op(_ls, *args, **kwargs)


def map(*args, **kwargs): return _generate_op(_map, *args, **kwargs)


def write(*args, **kwargs): return _generate_op(_write, *args, **kwargs)


def popd(*args, **kwargs): return _generate_op(_popd, *args, **kwargs)


def ps(*args, **kwargs): return _generate_op(_ps, *args, **kwargs)


def pushd(*args, **kwargs): return _generate_op(_pushd, *args, **kwargs)


def pwd(*args, **kwargs): return _generate_op(_pwd, *args, **kwargs)


def read(*args, **kwargs): return _generate_op(_read, *args, **kwargs)


def red(*args, **kwargs): return _generate_op(_red, *args, **kwargs)


def remote(*args, **kwargs): return _generate_op(_remote, *args, **kwargs)


def reverse(*args, **kwargs): return _generate_op(_reverse, *args, **kwargs)


def select(*args, **kwargs): return _generate_op(_select, *args, **kwargs)


def sort(*args, **kwargs): return _generate_op(_sort, *args, **kwargs)


def sql(*args, **kwargs): return _generate_op(_sql, *args, **kwargs)


def store(*args, **kwargs): return _generate_op(_store, *args, **kwargs)


def squish(*args, **kwargs): return _generate_op(_squish, *args, **kwargs)


def sudo(*args, **kwargs): return _generate_op(_sudo, *args, **kwargs)


def tail(*args, **kwargs): return _generate_op(_tail, *args, **kwargs)


def tee(*args, **kwargs): return _generate_op(_tee, *args, **kwargs)


def timer(*args, **kwargs): return _generate_op(_timer, *args, **kwargs)


def unique(*args, **kwargs): return _generate_op(_unique, *args, **kwargs)


def union(*args, **kwargs): return _generate_op(_union, *args, **kwargs)


def upload(*args, **kwargs): return _generate_op(_upload, *args, **kwargs)


def version(*args, **kwargs): return _generate_op(_version, *args, **kwargs)


def window(*args, **kwargs): return _generate_op(_window, *args, **kwargs)


# Utilities

def _generate_op(f, *args, **kwargs):
    op, arglist = f(*args, **kwargs)
    _ENV.op_modules[op.op_name()].args_parser(_ENV).parse(arglist, op)
    return _core.OpList(_MAIN.env, op)


def _run_pipeline(pipeline):
    command = marcel.core.Command(None, pipeline)
    try:
        command.execute(_ENV)
    except marcel.exception.KillCommandException as e:
        marcel.util.print_to_stderr(_ENV, e)
    except marcel.exception.KillAndResumeException:
        # Error handler printed the error
        pass


# Create a pipelines, by copying if necessary. The caller is going to append an op, and we
# don't want to modify the original.
def _prepare_pipeline(x):
    assert isinstance(x, _core.OpList)
    return x.create_pipeline()


def run(x):
    SHUTDOWN_HOOK.ensure_registered()
    pipeline = _prepare_pipeline(x)
    if not isinstance(pipeline.last_op(), _Write):
        pipeline.append(write().op)
    _run_pipeline(pipeline)


def gather(x, unwrap_singleton=True, errors=None):
    SHUTDOWN_HOOK.ensure_registered()
    pipeline = _prepare_pipeline(x)
    output = []
    terminal_op = _gather(output=output,
                          unwrap_singleton=unwrap_singleton,
                          errors=errors)
    pipeline.append(terminal_op)
    _run_pipeline(pipeline)
    return output


def first(x, unwrap_singleton=True, errors=None):
    SHUTDOWN_HOOK.ensure_registered()
    pipeline = _prepare_pipeline(x)
    output = []
    terminal_op = _first(output=output,
                         unwrap_singleton=unwrap_singleton,
                         errors=errors)
    pipeline.append(terminal_op)
    try:
        _run_pipeline(pipeline)
    except _exception.StopAfterFirst:
        pass
    first = None if len(output) == 0 else output[0]
    if isinstance(first, _error.Error):
        raise Exception(first)
    return first


def reservoir(name):
    assert type(name) is str
    assert name.isidentifier()
    reservoir = _reservoir.Reservoir(name, tempfile.mkstemp()[1])
    _RESERVOIRS.append(reservoir)
    return reservoir


def pos():
    return _ENV.current_op.pos()


o = marcel.structish.o
