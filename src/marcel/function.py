import marcel.env
import marcel.exception


class Function:

    symbols = {
        '+': lambda x, y: x + y,
        '*': lambda x, y: x * y,
        '^': lambda x, y: x ^ y,
        '&': lambda x, y: x & y,
        '|': lambda x, y: x | y,
        'and': lambda x, y: x and y,
        'or': lambda x, y: x or y,
        'max': lambda x, y: max(x, y),
        'min': lambda x, y: min(x, y),
        # Needed to support '.' notation for the red op. Function shouldn't be called.
        '.': lambda x, y: None
    }

    def __init__(self, source, globals):
        self.source = source.strip()
        self.globals = globals
        self.function = None
        self.op = None
        # create_function makes sure that the function source is correct, throwing an exception if not.
        self.create_function()

    def __repr__(self):
        return self.source

    def __call__(self, *args, **kwargs):
        # Unpickling preserves source but not function, (and doesn't call __init__),
        # so make sure we actually have a function.
        if self.function is None:
            self.create_function()
        assert self.function is not None
        try:
            return self.function(*args, **kwargs)
        except Exception as e:
            function_input = []
            if len(args) > 0:
                function_input.append(str(args))
            if len(kwargs) > 0:
                function_input.append(str(kwargs))
            function_input_string = ', '.join(function_input)
            raise marcel.exception.KillAndResumeException(self.op, function_input_string, str(e))

    def __getstate__(self):
        self.function = None
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__.update(state)

    def set_op(self, op):
        self.op = op

    def create_function(self):
        self.function = Function.symbols.get(self.source, None)
        if self.function is None:
            if self.source.split()[0] in ('lambda', 'lambda:'):
                self.function = eval(self.source, self.globals)
            else:
                try:
                    self.function = eval('lambda ' + self.source, self.globals)
                except Exception:
                    try:
                        self.function = eval('lambda: ' + self.source, self.globals)
                    except Exception:
                        raise marcel.exception.KillCommandException(
                            'Invalid function syntax: {}'.format(self.source))
