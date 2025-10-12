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

import inspect

import marcel.core
import marcel.env
import marcel.parser
import marcel.pipeline
import marcel.util

#------------------------------------------------------------------------------------------------------------
# Overview
#
# Using the CLI, a parenthesized Python expression is turned into a function by eval(source, namespace).
# The namespace implementation must implement nesting, to support pipeline args.
#
# NestedNamespace implements a nested namespace. It is a subclass of dict, so that it can be passed to eval.
# The dict contains all variable assignments in the current (innermost) scope. The NestedNamespace maintains
# a stack of Scopes, each recording the values of the pipeline params for that scope's pipeline.
#
# Scope is also a subclass of dict, for storing the pipeline param values. The values in a Scope's dict are
# actually EnvValues. These are designed to survive pickling/unpickling, so that they can be transmitted,
# e.g. to the process running a job. Note that the NestedNamespace dict can be reconstructed from the Scope
# dicts: gather the values from outermost to innermost, and unwrap. So on pickling, the NestedNamespace dict
# is cleared. On unpickling, it is reconstructed.


#------------------------------------------------------------------------------------------------------------
# Empty cache value

# Empty is used to denote an empty EnvValue cache. The weird isempty() test is needed because we could be
# checking an EnvValue's cache that originated in another process. So we can't rely on object identity,
# even for classes (I think). It is possible to use None to indicate an uncached EnvValue, but because None
# is a valid value for a variable, we could be reconstituting it repeatedly.

class Empty(object):

    def __repr__(self):
        return 'EMPTY'

EMPTY = Empty()

def isempty(x):
    t = type(x)
    return t.__module__ == 'marcel.nestednamespace' and t.__qualname__ == 'Empty'


#------------------------------------------------------------------------------------------------------------
# EnvValue

class EnvValue(object):

    def __init__(self, env, cached=EMPTY):
        assert not isinstance(cached, EnvValue), cached
        self.env = env
        self.cached = cached

    def __getstate__(self):
        self.env = None
        self.cached = EMPTY
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__.update(state)

    def unwrap(self):
        if isempty(self.cached):
            self.cached = self.reconstitute()
        return self.cached

    def reconstitute(self):
        assert False

    @staticmethod
    def wrap(env, value, source=None):
        def is_pipeline(value):
            return isinstance(value, marcel.pipeline.Pipeline)
        return (Function(env, value) if inspect.isbuiltin(value) else
                Module(env, value) if inspect.ismodule(value) else
                Compilable.for_function(env, f'({source})', value) if callable(value) else
                Compilable.for_pipeline(env, source, value) if is_pipeline(value) else
                Simple(env, value))

class Simple(EnvValue):

    def __init__(self, env, value):
        super().__init__(env, value)
        self.value = value

    def __repr__(self):
        return str(self.value)

    def reconstitute(self):
        return self.value


class Compilable(EnvValue):

    def __init__(self, env, source, compiled):
        assert source is not None
        assert compiled is not None
        super().__init__(env, compiled)
        self.source = source

    def __repr__(self):
        return self.source

    @staticmethod
    def for_function(env, source, function):
        assert callable(function), function
        return CompilableFunction(env, source, function)

    @staticmethod
    def for_pipeline(env, source, pipeline):
        assert isinstance(pipeline, marcel.pipeline.Pipeline), pipeline
        return CompilablePipeline(env, source, pipeline)


class CompilableFunction(Compilable):

    def reconstitute(self):
        assert self.env is not None
        function = marcel.parser.Parser(self.source, self.env).parse_function()
        # The variable owning this Compilable was assigned using this marcel syntax: var = (...).
        # The expression in the parens is evaluated and assigned to the var. For a CompilableFunction (this class),
        # that value is itself a function. That return value of parse_function() needs to be evaluated, similar to
        # what happened during the original assign op.
        return function()

    # A function-valued env var can be called as a function. In that case, env.getvar is bypassed and the Compilable
    # is invoked directly.
    def __call__(self, *args, **kwargs):
        function = self.unwrap()
        assert callable(function), function
        return function(*args, **kwargs)


class CompilablePipeline(Compilable):

    def reconstitute(self):
        assert self.env is not None
        return marcel.parser.Parser(self.source, self.env).parse_pipeline()


class Module(EnvValue):

    def __init__(self, env, module):
        super().__init__(env, module)
        self.module_name = module.__name__

    def __repr__(self):
        return self.module_name

    def reconstitute(self):
        return marcel.util.import_module(self.module_name)


class Import(EnvValue):

    def __init__(self, env, module, symbol, name, value):
        assert type(module) is str, module
        assert (symbol is None) or (type(symbol) is str), symbol
        assert name is None or type(name) is str
        super().__init__(env, value)
        self.module = module
        self.symbol = symbol
        self.name = name if name else symbol

    def __repr__(self):
        return (f'import({self.module}.{self.symbol})'
                if self.name == self.symbol else
                f'import({self.module}.{self.symbol} -> {self.name})')

    def reconstitute(self):
        return (marcel.util.import_module(self.module)
                if self.symbol is None else
                marcel.util.import_symbol(self.module, self.symbol))

class Function(EnvValue):

    def __init__(self, env, function):
        super().__init__(env, function)
        self.module_name = function.__module__
        self.function_name = function.__name__
        assert self.function_name.isidentifier(), self.function_name

    def __repr__(self):
        return f'{self.module_name}.{self.function_name}'

    def reconstitute(self):
        return marcel.util.import_symbol(self.module_name, self.function_name)


#------------------------------------------------------------------------------------------------------------
# NestedNamespace and Scope

BUILTINS = '__builtins__'

class Scope(dict):

    def __init__(self, env, parent=None, params=None):
        super().__init__()
        self.parent = parent
        self.params = [] if params is None else params
        self.env = env
        if parent is None:
            # Must be topmost scope
            self.level = 0
        else:
            assert type(parent) is Scope, parent
            self.level = parent.level + 1
            if params:
                for var in params:
                    self[var] = EnvValue.wrap(self.env, None)

    def __setitem__(self, key, value):
        if key != '__builtins__':
            self.store_item(key, value)

    def __repr__(self):
        return f'Scope({self.level}: {self.keys()})'

    def assign(self, var, value, source=None):
        assert not isinstance(value, EnvValue)
        self.store_item(var, EnvValue.wrap(self.env, value, source))

    def assign_import(self, var, module, symbol, value):
        assert not isinstance(value, EnvValue)
        self.store_item(var, Import(self.env, module, symbol, var, value))

    def delete(self, var):
        try:
            if self.parent is None or var in self.params:
                del self[var]
            else:
                self.parent.delete(var)
        except KeyError:
            pass

    def store_item(self, var, value):
        # About self.parent is not None: EnvValues are only needed for the outermost scope.
        if self.parent is not None and not isinstance(value, EnvValue):
            value = EnvValue.wrap(self.env, value)
        if self.parent is None or var in self.params:
            super().__setitem__(var, value)
        else:
            self.parent.store_item(var, value)

    # The vars assigned in this dict should be a subset of params
    def validate(self, label):
        if self.params:
            if not set(self.keys()).issubset(self.params):
                print(f'{label}: {self} assigns value to non-parameter')
                print(f'    scope params: {self.params}')
                print(f'    scope keys:   {self.keys()}')
            for var, x in self.items():
                if isinstance(x, EnvValue):
                    if isinstance(x.unwrap(), EnvValue):
                        print(f'{label}: Value of {var} is double-wrapped: {x}')
                else:
                    print(f'{label}: Value of {var} is unwrapped: {x}')


class NestedNamespace(dict):

    def __init__(self, env):
        super().__init__()
        self.env = env
        self.scopes = [Scope(env)]

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.current_scope()[key] = value

    def __delitem__(self, key):
        try:
            self.current_scope().delete(key)
        except KeyError:
            pass
        super().__delitem__(key)

    def __getstate__(self):
        assert len(self.scopes) == 1, len(self.scopes)
        return dict(self.scopes[0])

    def __setstate__(self, state):
        assert False

    def update(self, d):
        assert isinstance(d, dict)
        super().update(d)
        scope = self.current_scope()
        for key, value in d.items():
            scope[key] = value

    def assign(self, key, value, source=None):
        super().__setitem__(key, value)
        self.current_scope().assign(key, value, source)

    # Permanents don't need to be persisted, and exist at top-level. So they aren't stored in scopes.
    def assign_permanent(self, key, value):
        super().__setitem__(key, value)

    def assign_import(self, var, module, symbol, value):
        super().__setitem__(var, value)
        self.current_scope().assign_import(var, module, symbol, value)

    def n_scopes(self):
        return len(self.scopes)

    def push_scope(self, bindings):
        assert self.env
        self.scopes.append(Scope(self.env, self.current_scope(), bindings))
        if bindings:
            for var, value in bindings.items():
                self[var] = value

    def pop_scope(self):
        assert len(self.scopes) > 0
        # There are other ways to restore the namespace resulting from exiting the current scope.
        # This is simplest and not obviously too slow:
        # - Remove (var, value) entries for vars in the scope being popped.
        # - Insert (var, value) entries for remaining scopes, outermost first.
        popped_scope = self.scopes.pop()
        for var in popped_scope.keys():
            super().__delitem__(var)
        # Don't have to reset the topmost scope, and that can be problematic anyway, e.g. if env isn't
        # known and EnvValue cache is unset.
        for scope in self.scopes[1:]:
            for var, value in scope.items():
                super().__setitem__(var, value.unwrap())

    def current_scope(self):
        return self.scopes[-1]

    def reconstitute(self, persisted, env):
        assert len(self.scopes) == 1, len(self.scopes)
        scope = self.scopes[0]
        for var, value_wrapper in persisted.items():
            value_wrapper.env = env
            value_wrapper.reconstitute()
            super().__setitem__(var, value_wrapper.unwrap())
            scope.__setitem__(var, value_wrapper)

    # TODO: With set_env, is reconstitute needed? That's just an eager form of reconstitution.
    # TODO: Having the env available in all the EnvValues is a lazy form.
    def set_env(self, env):
        # This should only be called at the top level of execution, so there should only be one scope.
        assert len(self.scopes)== 1, len(self.scopes)
        scope = self.scopes[0]
        for value_wrapper in scope.values():
            value_wrapper.env = env


    # The NN dict maps environment variables to values. That mapping is the combined set of variable
    # assignments from the scopes, with an inner scope taking precedence over an outer scope (relevant
    # when the same var appears in two scopes.
    def validate(self, label=''):
        def remove_builtins(x):
            try:
                if isinstance(x, dict):
                    del x[BUILTINS]
                elif isinstance(x, set):
                    x.remove(BUILTINS)
            except KeyError:
                pass
            return x

        def visit_scope(scope, scope_union):
            # Visit the parent before adding this scope's vars. Inner scopes take precedence.
            if scope.parent:
                visit_scope(scope.parent, scope_union)
            scope.validate(label)
            for var, wrapper in scope.items():
                value = wrapper.unwrap()
                if type(value) is EnvValue:
                    print(f'{label}: {scope} contains doubly-wrapped value {wrapper}')
                scope_union[var] = value
        scope_union = dict()  # var -> value
        visit_scope(self.current_scope(), scope_union)
        namespace = remove_builtins(dict(self))
        if namespace != scope_union:
            print(f'{label}: Namespace does not match union of scopes')
            print(f'Namespace: {self}')
            print(f'Union of scopes: {scope_union}')
