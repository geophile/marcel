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

import sys

from marcel.exception import KillShellException

_USAGE = None


def _report_error(message):
    if _USAGE:
        print(_USAGE, file=sys.stderr)
    raise KillShellException(message)


class Arg(object):

    def __init__(self):
        self.envvar = None  # Filled in after construction

    def register_flags(self, all_flags):
        assert False

    def has_flag(self, flag):
        assert False


class AnonArg(Arg):

    def __init__(self, default):
        super().__init__()
        self.default = default
        self.required=False

    def __repr__(self):
        return 'AnonArg()'

    def register_flags(self, all_flags):
        return True

    def has_flag(self, flag):
        return False

    def is_anon(self):
        return True

    def is_boolean(self):
        return False


class FlagArg(AnonArg):

    def __init__(self, f1, f2, default, required):
        super().__init__(default)
        self.required = required
        assert f1 is not None
        self.short = None
        self.long = None
        if f2 is None:
            if FlagArg.short(f1):
                self.short = f1
            elif FlagArg.long(f1):
                self.long = f1
            else:
                assert False  # check_valid_flag calls should prevent us getting here
        else:
            if FlagArg.short(f1) and FlagArg.long(f2):
                self.short = f1
                self.long = f2
            elif FlagArg.long(f1) and FlagArg.short(f2):
                self.long = f1
                self.short = f2
            else:
                _report_error(f'If two flags are specified, one must be long and one must be short: {f1}, {f2}')
        self.boolean = False

    def __repr__(self):
        return (f'{self.short}|{self.long}' if self.short and self.long else
                self.short if self.short else
                self.long)

    def register_flags(self, all_flags):
        def register(flag):
            if flag is not None:
                if flag in all_flags:
                    _report_error(f'Duplicated flag: {flag}')
                else:
                    all_flags.add(flag)
        register(self.short)
        register(self.long)

    def has_flag(self, flag):
        return self.short == flag or self.long == flag

    def is_anon(self):
        return False

    @staticmethod
    def short(f):
        FlagArg.check_valid_flag(f)
        return f[0] == '-' and f[1] != '-'

    @staticmethod
    def long(f):
        FlagArg.check_valid_flag(f)
        return f[0] == '-' and f[1] == '-'

    @staticmethod
    def check_valid_flag(f):
        # Long enough
        if len(f) < 2:
            _report_error(f'Invalid flag: {f}')
        # Not just -
        if f.startswith('--'):
            f = f[2:]
        elif f.startswith('-'):
            f = f[1:]
        if len(f) == 0:
            _report_error(f'Invalid flag: {f}')


class BooleanFlagArg(FlagArg):

    def __init__(self, short, long, default, required):
        super().__init__(short, long, default, required)
        self.boolean = True

    def __repr__(self):
        flag_str = super().__repr__()
        return f'BooleanFlag{flag_str[flag_str.find("("):]}'

    def is_boolean(self):
        return True


class CommandLine(object):

    def __init__(self, usage, **var_arg):
        global _USAGE
        _USAGE = usage
        self.var_arg = var_arg
        anon_seen = False
        for var, arg in self.var_arg.items():
            if not (type(var) is str and var.isidentifier()):
                _report_error(f'Var must be valid as a Python identifier: {var}')
            if type(arg) not in (AnonArg, FlagArg, BooleanFlagArg):
                _report_error(f'Arg value must be flag(), boolean_flag(), or anon(): {arg}')
            if arg.is_anon():
                if anon_seen:
                    _report_error('Too many anon() specified.')
                else:
                    anon_seen = True
            arg.envvar = var
        all_flags = set()
        for arg in self.var_arg.values():
            arg.register_flags(all_flags)
        # If register_flags didn't raise an exception, there are no duplicates

    def parse(self, argv):
        def isflag(arg):
            return arg.startswith('-')

        def arg_of(flag):
            for arg in self.var_arg.values():
                if arg.has_flag(flag):
                    return arg
            _report_error(f'Unrecognized flag: {flag}')

        def anon_arg():
            for arg in self.var_arg.values():
                if arg.is_anon():
                    return arg
            return None

        # Generator yielding one of:
        # - (arg, True)
        # - (arg, value)
        # - (None, value)
        # where arg is the Arg corresponding to an observed flag.
        def token_scan():
            a = 0
            while a < len(argv):
                token = argv[a]
                a += 1
                if isflag(token):
                    arg = arg_of(token)
                    if arg.is_boolean():
                        # arg is boolean flag
                        yield arg, True
                    else:
                        # arg is flag expecting a value
                        if a == len(argv):
                            _report_error(f'Value missing for flag: {token}')
                        else:
                            x = argv[a]
                            if isflag(x):
                                _report_error(f'Value missing for flag: {arg}')
                            else:
                                a += 1
                                yield arg, x
                else:
                    yield None, token

        values = {}  # envvar -> value (from command line)
        anon = []
        # Fill in defaults
        for arg in self.var_arg.values():
            if not arg.required:
                values[arg.envvar] = arg.default
        # Fill in supplied values
        for arg, value in token_scan():
            if arg is None:
                anon.append(value)
            else:
                values[arg.envvar] = value
        if anon_arg():
            # Skip marcel invocation and script name
            values[anon_arg().envvar] = anon[2:]
        # Check that required values were provided
        for arg in self.var_arg.values():
            if arg.required and arg.envvar not in values:
                _report_error(f'No value specified for required flag: {arg}')
        return values

def parse_args(env, usage, **kwargs):
    var_val = CommandLine(usage, **kwargs).parse(sys.argv)
    for k, v in var_val.items():
        env.setvar(k, v)
    argv = sys.argv[1:]
    env.setvar('ARGV', argv)
    return argv

def flag(f1, f2=None, default=None, required=False):
    return FlagArg(f1, f2, default=default, required=required)


def boolean_flag(f1, f2=None, default=False):
    return BooleanFlagArg(f1, f2, default=default, required=False)


def anon():
    return AnonArg(default=list())
