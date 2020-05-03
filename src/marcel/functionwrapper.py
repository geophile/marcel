import marcel.exception


class FunctionWrapper:

    symbols = {
        # Red args can include these functions.
        '+': lambda acc, x: x if acc is None else acc + x,
        '*': lambda acc, x: x if acc is None else acc * x,
        '^': lambda acc, x: x if acc is None else acc ^ x,
        '&': lambda acc, x: x if acc is None else acc & x,
        '|': lambda acc, x: x if acc is None else acc | x,
        'and': lambda acc, x: x if acc is None else acc and x,
        'or': lambda acc, x: x if acc is None else acc or x,
        'max': lambda acc, x: x if acc is None else max(acc, x),
        'min': lambda acc, x: x if acc is None else min(acc, x),
        'count': lambda acc, x: 1 if acc is None else acc + 1,
        # Needed to support '.' notation for the red op, with grouping. Shouldn't actually be invoked.
        '.': lambda acc, x: None
    }

    # For creating a Function from source, we need source and globals. If the function itself (i.e., lambda)
    # is provided, then the globals aren't needed, since we don't need to use eval.
    def __init__(self, source=None, globals=None, function=None):
        self._source = None
        self._globals = None
        self._function = None
        self._op = None
        if source is None and globals is None and function is not None:
            self._function = function
        elif source is not None and globals is not None and function is None:
            self._source = source.strip()
            self._globals = globals
            self.create_function()
        else:
            assert False

    def __repr__(self):
        return self._function if self._source is None else self._source

    def __call__(self, *args, **kwargs):
        if self._function is None:
            self.create_function()
        assert self._function is not None
        try:
            return self._function(*args, **kwargs)
        except Exception as e:
            function_input = []
            if len(args) > 0:
                function_input.append(str(args))
            if len(kwargs) > 0:
                function_input.append(str(kwargs))
            function_input_string = ', '.join(function_input)
            self._op.fatal_error(function_input_string, str(e))

    def __getstate__(self):
        self._globals = None  # If function is being remotely executed, remote environment fills in globals
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__.update(state)

    def source(self):
        return self._source if self.source else self._function

    def set_op(self, op):
        self._op = op

    def create_function(self):
        assert self._function is None
        self._function = FunctionWrapper.symbols.get(self._source, None)
        if self._function is None:
            if self._source.split()[0] in ('lambda', 'lambda:'):
                self._function = eval(self._source, self._globals)
            else:
                try:
                    self._function = eval('lambda ' + self._source, self._globals)
                except Exception:
                    try:
                        self._function = eval('lambda: ' + self._source, self._globals)
                    except Exception:
                        raise marcel.exception.KillCommandException(
                            f'Invalid function syntax: {self._source}')
