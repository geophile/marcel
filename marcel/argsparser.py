# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, (or at your
# option) any later version.
# 
# Marcel is distributed ax the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Marcel.  If not, see <https://www.gnu.org/licenses/>.

import pathlib

import marcel.core
import marcel.exception
import marcel.function
import marcel.object.cluster
import marcel.object.file
import marcel.reservoir
import marcel.stringliteral
import marcel.util

# A marcel op has arguments. An argument is one of:
#    - An optional flag with no value
#    - An optional flag with one value
#    - An optional flag with an optional value
#    - An anonymous value: not preceded by a flag
# If an optional flag is followed by a value that is not a flag, then the
# value is assumed to be a value of the flag, not anonymous.
#
# Constraints on groups of flags:
#     - At most one must be specified
#     - Exactly one must be specified
# Additional constraints can be checked by the op.

VALUE_NONE = 1
VALUE_ONE = 2
VALUE_OPTIONAL = 3
NO_DEFAULT = object()


# ----------------------------------------------------------------------------------------------------------------------

# Args

class ArgsError(marcel.exception.KillCommandException):

    def __init__(self, op_name, message):
        super().__init__(f'Operator {op_name}: {message}')


class Arg:

    def __init__(self, op_name, name, convert, target):
        assert name is not None
        self.op_name = op_name
        self.name = name
        self.target = target if target else name
        self.convert = convert if convert else Arg.eval_if_string_listeral

    def __repr__(self):
        return self.name

    @staticmethod
    def eval_if_string_listeral(_, x):
        return marcel.util.string_value(x) if type(x) is marcel.stringliteral.StringLiteral else x


class Flag(Arg):

    NO_DEFAULT = object()

    def __init__(self, op_name, name, convert, short, long, value, target=None, default=True):
        super().__init__(op_name, name, convert, target)
        assert short is not None or long is not None
        assert short is None or len(short) == 2 and short[0] == '-' and short[1] != '-'
        assert long is None or len(long) >= 3 and long[:2] == '--' and long[2] != '-'
        assert value in (VALUE_NONE, VALUE_ONE, VALUE_OPTIONAL)
        self.short = short
        self.long = long
        self.value = value
        self.default = default

    def __repr__(self):
        return (f'{self.short}|{self.long}' if self.short and self.long else
                self.short if self.short else
                self.long)

    @staticmethod
    def plausible(x):
        if not isinstance(x, str):
            return False
        if len(x) < 2:
            return False
        return x[0] == '-'


class Anon(Arg):

    def __init__(self, op_name, name, convert, default, target=None):
        super().__init__(op_name, name, convert, target)
        self.default = default


class AnonList(Arg):

    def __init__(self, op_name, name, convert, target=None):
        super().__init__(op_name, name, convert, target)


# ----------------------------------------------------------------------------------------------------------------------

# Interface

class ArgsParser:

    def __init__(self, op_name, env):
        self.op_name = op_name
        self.env = env
        self.flag_args = []
        self.anon_args = []
        self.anon_list_arg = None
        self.at_most_one_names = []
        self.exactly_one_names = []
        self.validated = False
        # A hack to sneak the op currently being validated to function()
        self.current_op = None

    def add_flag_no_value(self, name, short, long, target=None):
        self.flag_args.append(Flag(self.op_name, name, None, short, long, VALUE_NONE, target))

    def add_flag_one_value(self, name, short, long, convert=None, target=None):
        self.flag_args.append(Flag(self.op_name, name, convert, short, long, VALUE_ONE, target))

    def add_flag_optional_value(self, name, short, long, default, convert=None, target=None):
        self.flag_args.append(Flag(self.op_name, name, convert, short, long, VALUE_OPTIONAL, target, default))

    def add_anon(self, name, convert=None, default=NO_DEFAULT, target=None):
        self.anon_args.append(Anon(self.op_name, name, convert, default, target))

    def add_anon_list(self, name, convert=None, target=None):
        self.anon_list_arg = AnonList(self.op_name, name, convert, target)

    def at_most_one(self, *names):
        self.at_most_one_names.append(self.name_set(names))

    def exactly_one(self, *names):
        self.exactly_one_names.append(self.name_set(names))

    def validate(self):
        self.check_flag_symbols_unique()
        self.check_arg_names_unique()
        self.check_anon_order()
        self.check_anon_list_terminal()
        self.validated = True

    # For TabCompleter
    def flags(self):
        flags = []
        for flag in self.flag_args:
            if flag.short:
                flags.append(flag.short)
            if flag.long:
                flags.append(flag.long)
        return flags

    # ------------------------------------------------------------------------------------------------------------------

    # Conversion and type checking

    def str_to_int(self, arg, x):
        if type(x) is int or callable(x):
            return x
        if isinstance(x, str):
            try:
                return int(x)
            except ValueError:
                raise ArgsError(arg.op_name, f'{arg.name} cannot be converted to int: {x}')
        raise ArgsError(arg.op_name, f'{arg.name} must be an int: {x}')

    def to_float(self, arg, x):
        if type(x) is float or callable(x):
            return x
        if type(x) is int or str:
            try:
                return float(x)
            except ValueError:
                raise ArgsError(arg.op_name, f'{arg.name} cannot be converted to float: {x}')
        raise ArgsError(arg.op_name, f'{arg.name} must be a string: {x}')

    def str_to_bool(self, arg, x):
        if type(x) is bool or callable(x):
            return x
        if isinstance(x, str):
            return x in ('T', 't', 'True', 'true')
        raise ArgsError(arg.op_name, f'{arg.name} must be a string: {x}')

    def check_str(self, arg, x):
        if isinstance(x, str):
            x = marcel.util.string_value(x)
        elif callable(x):
            pass
        else:
            raise ArgsError(arg.op_name, f'{arg.name} must be a string: {x}')
        return x

    def check_str_or_file(self, arg, x):
        if isinstance(x, str):
            x = marcel.util.string_value(x)
        elif(isinstance(x, marcel.object.file.File) or
             isinstance(x, pathlib.Path) or
             callable(x)):
            pass
        else:
            raise ArgsError(arg.op_name, f'{arg.name} must be a string: {x}')
        return x

    def check_pipeline(self, arg, x):
        if self.env.api_usage() and (callable(x) or type(x) is marcel.core.OpList):
            # There should be more checking later, regarding the number of args
            return x
        if ((not self.env.api_usage()) and
            marcel.util.one_of(x, (str, marcel.core.PipelineExecutable, marcel.core.PipelineFunction))):
            # str: Presumably the name of a variable bound to a pipelines
            return x
        raise marcel.argsparser.ArgsError(self.op_name,
                                          f'{arg.name} argument must be a Pipeline: {x}')

    def fork_gen(self, arg, x):
        if type(x) is int or callable(x):
            return x
        elif type(x) is marcel.object.cluster.Cluster:
            return x
        elif isinstance(x, str):
            try:
                return int(x)
            except ValueError:
                # Could be a cluster name
                cluster = self.env.cluster(x)
                return cluster if cluster else marcel.util.string_value(x)
        elif marcel.util.iterable(x):
            return x
        raise ArgsError(arg.op_name, f'{x} must be an int, iterable, or Cluster')

    def cluster(self, arg, x):
        cluster = None
        if type(x) is marcel.object.cluster.Cluster:
            cluster = x
        elif isinstance(x, str):
            cluster = self.env.cluster(marcel.util.string_value(x))
        else:
            pass
        if cluster is None:
            raise ArgsError(arg.op_name, f'{x} is not a Cluster')
        return cluster

    # An ArgsParser subclass uses this function as the value of convert, to validate
    # Python expressions, (parser.Expression). f is function source for console usage,
    # a callable for API usage.
    def function(self, arg, x):
        f = None
        if isinstance(x, marcel.function.Function):
            f = x
        elif callable(x):
            f = marcel.function.NativeFunction(function=x)
        elif isinstance(x, str):
            x = marcel.util.unescape(x)
            try:
                f = marcel.function.SymbolFunction(x)
            except KeyError:
                # Could be a function name, which should be in the environment
                xval = self.env.getvar(x)
                if callable(xval):
                    f = marcel.function.NativeFunction(function=xval)
        if f is None:
            raise ArgsError(arg.op_name, f'{arg.name} argument must be a function.')
        return f

    def function_or_pipeline(self, arg, x):
        try:
            a = self.function(arg, x)
        except ArgsError as fe:
            try:
                a = self.check_pipeline(arg, x)
            except ArgsError as pe:
                raise ArgsError(arg.op_name, f'{arg.name} is neither a function nor a pipeline')
        assert a is not None, x
        return a

    # ------------------------------------------------------------------------------------------------------------------

    # Parsing

    def parse(self, args, op):
        assert self.validated
        self.current_op = op
        flags, anon, anon_list = self.extract_flags_and_anon(args)
        # Compute the set of names for supplied args
        names = list(flags.keys())
        names.extend(anon.keys())
        if len(anon_list) > 0:
            self.check_anon_list_ok(anon_list)
            names.append(self.anon_list_arg)
        names = set(names)
        self.check_value_counts(flags)
        self.check_at_most_one_constraints(names)
        self.check_exactly_one_constraints(names)
        self.complete_anon_processing(anon, anon_list)
        # Transfer args to op
        op_dict = op.__dict__
        for k, v in flags.items():
            arg = self.find_by_name(k)
            op_dict[arg.target] = v
        for k, v in anon.items():
            arg = self.find_by_name(k)
            op_dict[arg.target] = v

    # ------------------------------------------------------------------------------------------------------------------

    # Utilities

    def find_flag(self, x):
        if isinstance(x, str):
            for flag in self.flag_args:
                if flag.short == x or flag.long == x:
                    return flag
        return None

    def find_by_name(self, name):
        for flag in self.flag_args:
            if flag.name == name:
                return flag
        for anon in self.anon_args:
            if anon.name == name:
                return anon
        if self.anon_list_arg.name == name:
            return self.anon_list_arg
        return None

    def name_set(self, names):
        name_set = set()
        for name in names:
            assert (name in [flag.name for flag in self.flag_args] or
                    name in [anon.name for anon in self.anon_args]), name
            name_set.add(name)
        assert len(names) == len(name_set)
        return name_set

    # Can expand -xyz to -f -y -z when -f, -y, and -z are all no-value flags.
    def expand_arg(self, arg):
        if isinstance(arg, str) and len(arg) > 2 and arg[0] == '-' and arg[1] != '-':
            args = []
            for x in arg[1:]:
                flag = '-' + x
                if self.find_flag(flag):
                    args.append(flag)
                else:
                    return [arg]
            return args
        else:
            return [arg]

    # ------------------------------------------------------------------------------------------------------------------

    # Validation steps

    # Check that there is no duplication among all the short and long flags.
    def check_flag_symbols_unique(self):
        flags = set()
        for flag in self.flag_args:
            if flag.short:
                assert flag.short not in flags
                flags.add(flag.short)
            if flag.long:
                assert flag.long not in flags
                flags.add(flag.long)

    # Check that arg names are unique. (They will end up as attributes of an op.)
    def check_arg_names_unique(self):
        names = set()
        for flag in self.flag_args:
            assert flag.name not in names
            names.add(flag.name)
        for anon in self.anon_args:
            assert anon.name not in names
            names.add(anon.name)
        if self.anon_list_arg:
            assert self.anon_list_arg.name not in names

    # Anon args have to appear in the order declared. Anons that don't have default values are mandatory
    # and must precede those that do have defaults, (which can be omitted).
    def check_anon_order(self):
        no_default = True
        for anon in self.anon_args:
            if no_default and anon.default is not NO_DEFAULT:
                no_default = False
            assert no_default == (anon.default is NO_DEFAULT)

    # Anons before the terminal list of anons must be mandatory. (Otherwise we can't tell where the list begins.)
    def check_anon_list_terminal(self):
        if self.anon_list_arg is not None:
            for anon in self.anon_args:
                assert anon.default == NO_DEFAULT

    # ------------------------------------------------------------------------------------------------------------------

    # Parsing steps

    def extract_flags_and_anon(self, args):
        args_iterator = iter(args)
        flags = {}  # arg name -> value
        anon = {}  # arg name -> value
        anon_list = []
        current_flag_arg = None
        flag_ok = len(self.flag_args) > 0
        try:
            while True:
                for arg in self.expand_arg(next(args_iterator)):
                    flag_arg = self.find_flag(arg)
                    if flag_arg:
                        # Flag
                        if flag_ok:
                            if flag_arg.name not in flags:
                                flags[flag_arg.name] = flag_arg.default
                                current_flag_arg = flag_arg
                            else:
                                raise ArgsError(self.op_name, f'{arg} specified more than once.')
                        else:
                            raise ArgsError(self.op_name, 'Flags must all appear before the first anonymous arg')
                    elif Flag.plausible(arg) and flag_ok:
                        # Unknown flag
                        raise ArgsError(self.op_name, f'Unknown flag {arg}')
                    else:
                        # Flag value or anon
                        if current_flag_arg is None or current_flag_arg.value == VALUE_NONE:
                            if len(anon) >= len(self.anon_args):
                                # Anon list
                                if self.anon_list_arg:
                                    anon_list.append(self.anon_list_arg.convert(self.anon_list_arg, arg))
                                else:
                                    raise ArgsError(self.op_name, f'Too many anonymous args.')
                            else:
                                # Anon
                                anon_arg = self.anon_args[len(anon)]
                                anon[anon_arg.name] = anon_arg.convert(anon_arg, arg)
                            flag_ok = False
                        else:
                            # Flag value
                            flags[current_flag_arg.name] = current_flag_arg.convert(current_flag_arg, arg)
                            current_flag_arg = None
        except StopIteration:
            pass
        except Exception as e:
            if current_flag_arg:
                raise ArgsError(self.op_name, f'flag {current_flag_arg}: {e}')
            else:
                raise ArgsError(self.op_name, f'{type(e)}: {str(e)}')
        return flags, anon, anon_list

    # An anon list is permitted only if declared
    def check_anon_list_ok(self, anon_list):
        if self.anon_list_arg is None and len(anon_list) > 0:
            raise ArgsError(self.op_name, f'There are unexpected args: {anon_list}')

    # Check that values were supplied exactly when permitted or required.
    def check_value_counts(self, flags):
        for flag_name, value in flags.items():
            flag_arg = self.find_by_name(flag_name)
            # We found the flag searching by the short or long form. So lookup by name must work.
            assert flag_arg, flag_name
            if flag_arg.value == VALUE_ONE and value is True:
                raise ArgsError(self.op_name, f'{flag_arg} requires a value.')
            if flag_arg.value == VALUE_NONE and value is not True:
                raise ArgsError(self.op_name, f'{flag_arg} must not provide a value.')

    def check_at_most_one_constraints(self, names):
        for group in self.at_most_one_names:
            if len(group.intersection(names)) > 1:
                description = '{' + ', '.join([str(self.find_by_name(name)) for name in group]) + '}'
                raise ArgsError(self.op_name, f'Cannot specify more than one of {description}')

    def check_exactly_one_constraints(self, names):
        for group in self.exactly_one_names:
            if len(group.intersection(names)) != 1:
                description = '{' + ', '.join([str(self.find_by_name(name)) for name in group]) + '}'
                raise ArgsError(self.op_name, f'Must specify exactly one of {description}')

    # - Check that required anons have been specified.
    # - Fill in defaults for unspecified anon args.
    # - Append anon_list to anons.
    def complete_anon_processing(self, anon, anon_list):
        assert len(anon) <= len(self.anon_args)
        while len(anon) < len(self.anon_args):
            anon_arg = self.anon_args[len(anon)]
            if anon_arg.default == NO_DEFAULT:
                raise ArgsError(self.op_name, f'No value specified for {anon_arg.name}.')
            anon[anon_arg.name] = anon_arg.default
        if self.anon_list_arg:
            anon[self.anon_list_arg.name] = anon_list


class PipelineArgsParser:

    def __init__(self, var):
        self.var = var

    def parse_pipeline_args(self, op_args):
        args = []
        kwargs = {}
        param_name = None
        flags_done = None
        for arg in op_args:
            flag_name = PipelineArgsParser.flag_name(arg)
            if flag_name:
                if flags_done:
                    raise ArgsError(self.var, f'Flag {flag_name} appears after anonymous arguments.')
                param_name = flag_name
            else:
                if param_name is None:
                    flags_done = True
                    args.append(arg)
                else:
                    if param_name in kwargs:
                        raise ArgsError(self.var, f'Flag {param_name} given more than once.')
                    kwargs[param_name] = arg
                    param_name = None
        return args, kwargs

    @staticmethod
    def flag_name(arg):
        name = (None if not isinstance(arg, str) else
                arg[2:] if arg.startswith('--') else
                arg[1:] if arg.startswith('-') else
                None)
        return name if name and name.isidentifier() else None
