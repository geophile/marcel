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

from enum import Enum, auto

import marcel.core
import marcel.exception
import marcel.functionwrapper
import marcel.opmodule
import marcel.util


# ----------------------------------------------------------------------------------------------------------------------

# Parsing errors

class UnexpectedTokenError(marcel.exception.KillCommandException):

    SNIPPET_SIZE = 10

    def __init__(self, token, message):
        super().__init__(message)
        self.token = token
        self.message = message

    def __str__(self):
        if self.token is None:
            return f'Premature end of input: {self.message}'
        else:
            token_start = self.token.start
            token_text = self.token.text
            snippet_start = max(token_start - UnexpectedTokenError.SNIPPET_SIZE, 0)
            snippet_end = max(token_start + UnexpectedTokenError.SNIPPET_SIZE + 1, len(token_text))
            snippet = token_text[snippet_start:snippet_end]
            return f'Parsing error at position {token_start - snippet_start} of "...{snippet}...": {self.message}'


class PrematureEndError(Exception):

    def __init__(self):
        super().__init__()

    def __str__(self):
        return 'Command ended prematurely.'


class UnknownOpError(marcel.exception.KillCommandException):

    def __init__(self, op_name):
        super().__init__(op_name)
        self.op_name = op_name

    def __str__(self):
        return f'Unknown command: {self.op_name}'


class MalformedStringError(marcel.exception.KillCommandException):

    def __init__(self, text, message):
        super().__init__(message)
        self.text = text


class ParseError(marcel.exception.KillCommandException):

    def __init__(self, message):
        super().__init__(message)


# ----------------------------------------------------------------------------------------------------------------------

# Tokens

class Source:
    def __init__(self, text, position=0):
        self.text = text
        self.start = position
        self.end = position

    def __repr__(self):
        name = self.__class__.__name__
        if self.start is None or self.end is None:
            text = '' if self.text is None else self.text
        else:
            assert self.text is not None
            text = self.text[self.start:self.end]
        return f'{name}({text})'

    def peek_char(self):
        c = None
        if self.end < len(self.text):
            c = self.text[self.end]
        return c

    def next_char(self):
        c = None
        if self.end < len(self.text):
            c = self.text[self.end]
            self.end += 1
        return c

    def remaining(self):
        return len(self.text) - self.end


class Token(Source):
    # Special characters that need to be escaped for python strings
    ESCAPABLE = '''\\\'\"\a\b\f\n\r\t\v'''
    SINGLE_QUOTE = "'"
    DOUBLE_QUOTE = '"'
    QUOTES = SINGLE_QUOTE + DOUBLE_QUOTE
    ESCAPE_CHAR = '\\'
    OPEN = '('
    CLOSE = ')'
    PIPE = '|'
    BANG = '!'
    FORK = '@'
    BEGIN = '['
    END = ']'
    ASSIGN = '='
    STRING_TERMINATING = [OPEN, CLOSE, PIPE, BEGIN, END, ASSIGN]

    def __init__(self, text, position, adjacent_to_previous):
        super().__init__(text, position)
        self.adjacent_to_previous = adjacent_to_previous

    def is_string(self):
        return False

    def is_fork(self):
        return False

    def is_bang(self):
        return False

    def is_pipe(self):
        return False

    def is_expr(self):
        return False

    def is_begin(self):
        return False

    def is_end(self):
        return False

    def is_assign(self):
        return False

    def value(self):
        return None

    def op_name(self):
        return None


# PythonString isn't a top-level token that appears on a command line. An Expression is defined as
# everything in between a top-level ( and the matching ). Everything delimited by those parens is
# simply passed to Python's eval. However, in order to do the matching, any parens inside a Python
# string (which could be part of the Expression) must be ignored.
#
# Python string literals are specified here:
# https://docs.python.org/3/reference/lexical_analysis.html#string-and-bytes-literals.
class PythonString(Token):

    def __init__(self, text, position, adjacent_to_previous):
        super().__init__(text, position, adjacent_to_previous)
        self.string = None
        self.scan()

    def __repr__(self):
        return self.string

    def value(self):
        return self.string

    # TODO: string prefixes
    # TODO: Multiline (triple quoted only)
    # TODO: \octal
    # TODO: \hex
    # TODO: \N
    # TODO: \u
    # TODO: \U
    def scan(self):
        chars = []
        quote = self.next_char()
        assert quote in Token.QUOTES
        triple_quote = self.advance_if_triple(quote)
        while True:
            c = self.next_char()
            if c is None:
                raise MalformedStringError(self.text, "Not a python string")
            elif c in Token.QUOTES:
                # Possible ending quoted sequence
                if c == quote:
                    if triple_quote:
                        if self.advance_if_triple(quote):
                            # Ended triple quote
                            break
                        else:
                            chars.append(c)
                    else:
                        # Ended single quote
                        break
                else:
                    chars.append(c)
            elif c == Token.ESCAPE_CHAR:
                c = self.next_char()
                if c in Token.ESCAPABLE:
                    chars.append(c)
                else:
                    chars.append(Token.ESCAPE_CHAR)
                    chars.append(c)
            elif c.isspace():
                if quote:
                    # Space is inside quoted sequence
                    chars.append(c)
                else:
                    break
            else:
                chars.append(c)
        self.string = ''.join(chars)

    def advance_if_triple(self, quote):
        assert quote is not None
        if self.remaining() >= 2 and self.text[self.end:self.end + 2] == quote * 2:
            self.end += 2
            return True
        else:
            return False


class Expression(Token):

    def __init__(self, text, position, adjacent_to_previous, globals):
        super().__init__(text, position, adjacent_to_previous)
        self._globals = globals
        self._source = None
        self._function = None
        self.scan()

    def is_expr(self):
        return True

    def value(self):
        if self._function is None:
            source = self.source()
            if source.split()[0] in ('lambda', 'lambda:'):
                function = eval(source, self._globals)
            else:
                try:
                    function = eval('lambda ' + source, self._globals)
                except Exception:
                    try:
                        function = eval('lambda: ' + source, self._globals)
                    except Exception:
                        raise marcel.exception.KillCommandException(f'Invalid function syntax: {source}')
            self._function = marcel.functionwrapper.FunctionWrapper(function=function)
        return self._function
    
    def source(self):
        if self._source is None:
            self._source = self.text[self.start + 1:self.end - 1]
        return self._source

    def scan(self):
        c = self.next_char()
        assert c == Token.OPEN
        nesting = 1
        while nesting > 0:
            c = self.next_char()
            if c is None:
                break
            elif c == Token.OPEN:
                nesting += 1
            elif c == Token.CLOSE:
                nesting -= 1
            elif c in Token.QUOTES:
                self.end = PythonString(self.text, self.end - 1, False).end
        if self.text[self.end - 1] != Token.CLOSE:
            raise marcel.exception.KillCommandException(
                f'Malformed Python expression {self.text[self.start:self.end]}')


class String(Token):

    def __init__(self, text, position, adjacent_to_previous):
        super().__init__(text, 0 if position is None else position, adjacent_to_previous)
        if position is None:
            # Text is fine as is.
            self.string = text
        else:
            # Text is from the input being parsed. Scan it to deal with escapes and quotes.
            self.string = None
            self.scan()

    def is_string(self):
        return True

    def value(self):
        return self.string

    def op_name(self):
        # This should only being called for the first op following START
        return self.string

    def scan(self):
        quote = None
        chars = []
        while True:
            c = self.next_char()
            if c is None:
                break
            elif c.isspace() or c in Token.STRING_TERMINATING:
                if quote is None:
                    # c is part of the next token
                    self.end -= 1
                    break
                else:
                    chars.append(c)
            elif c in Token.QUOTES:
                if quote is None:
                    quote = c
                elif c == quote:
                    quote = None
                else:
                    chars.append(c)
            elif c == Token.ESCAPE_CHAR:
                if quote is None:
                    # TODO: ESCAPE at end of line
                    c = self.next_char()
                    chars.append(c)
                elif quote == Token.SINGLE_QUOTE:
                    chars.append(c)
                elif quote == Token.DOUBLE_QUOTE:
                    # TODO: no next char
                    c = self.next_char()
                    # TODO: Other escaped chars inside double quotes
                    if c == Token.ESCAPE_CHAR:
                        chars.append(c)
                    else:
                        chars.append(Token.ESCAPE_CHAR)
                        chars.append(c)
                else:
                    raise marcel.exception.KillCommandException(
                        f'Malformed string: {self.text[self.start:self.end]}')
            else:
                chars.append(c)
        self.string = ''.join(chars)


class Run(Token):

    def __init__(self, text, position, adjacent_to_previous):
        super().__init__(text, position, adjacent_to_previous)
        self.symbol = None
        self.scan()  # Sets self.symbol

    def value(self):
        return self.symbol

    def op_name(self):
        return 'run'

    def is_bang(self):
        return True

    def scan(self):
        c = self.next_char()
        assert c == Token.BANG
        c = self.peek_char()
        if c == Token.BANG:
            self.next_char()
            self.symbol = '!!'
        else:
            self.symbol = '!'


class OneCharSymbol(Token):

    def __init__(self, text, position, adjacent_to_previous, symbol):
        super().__init__(text, position, adjacent_to_previous)
        self.symbol = symbol
        self.end += 1

    def value(self):
        return self.symbol


class Pipe(OneCharSymbol):

    def __init__(self, text, position, adjacent_to_previous):
        super().__init__(text, position, adjacent_to_previous, Token.PIPE)

    def is_pipe(self):
        return True


class Fork(OneCharSymbol):

    def __init__(self, text, position, adjacent_to_previous):
        super().__init__(text, position, adjacent_to_previous, Token.FORK)

    def is_fork(self):
        return True

    def op_name(self):
        return 'fork'


class Begin(OneCharSymbol):

    def __init__(self, text, position, adjacent_to_previous):
        super().__init__(text, position, adjacent_to_previous, Token.BEGIN)

    def is_begin(self):
        return True


class End(OneCharSymbol):

    def __init__(self, text, position, adjacent_to_previous):
        super().__init__(text, position, adjacent_to_previous, Token.END)

    def is_end(self):
        return True


class Assign(OneCharSymbol):

    def __init__(self, text, position, adjacent_to_previous):
        super().__init__(text, position, adjacent_to_previous, Token.ASSIGN)

    def is_assign(self):
        return True

    def op_name(self):
        return 'assign'


class ImpliedMap(Token):

    def __init__(self):
        super().__init__(None, None, False)

    def op_name(self):
        return 'map'


# ----------------------------------------------------------------------------------------------------------------------

# Lexing


class Lexer(Source):

    def __init__(self, env, text):
        super().__init__(text)
        self.env = env

    def tokens(self):
        tokens = []
        token = self.next_token()
        while token is not None:
            tokens.append(token)
            token = self.next_token()
        return self.consolidate_adjacent(tokens)

    def next_token(self):
        token = None
        skipped = self.skip_whitespace()
        c = self.peek_char()
        if c is not None:
            adjacent_to_previous = self.end > 0 and skipped == 0
            if c == Token.OPEN:
                token = Expression(self.text, self.end, adjacent_to_previous, self.env.namespace)
            elif c == Token.CLOSE:
                raise ParseError('Unmatched )')
            elif c == Token.PIPE:
                token = Pipe(self.text, self.end, adjacent_to_previous)
            elif c == Token.BEGIN:
                token = Begin(self.text, self.end, adjacent_to_previous)
            elif c == Token.END:
                token = End(self.text, self.end, adjacent_to_previous)
            elif c == Token.FORK:
                token = Fork(self.text, self.end, adjacent_to_previous)
            elif c == Token.BANG:
                token = Run(self.text, self.end, adjacent_to_previous)
            elif c == Token.ASSIGN:
                token = Assign(self.text, self.end, adjacent_to_previous)
            else:
                token = String(self.text, self.end, adjacent_to_previous)
            self.end = token.end
        return token

    def skip_whitespace(self):
        before = self.end
        c = self.peek_char()
        while c is not None and c.isspace():
            self.next_char()
            c = self.peek_char()
        after = self.end
        return after - before

    # Adjacent String and Expression tokens must be consolidated. Turn them into an Expression that concatenates
    # the values.
    def consolidate_adjacent(self, tokens):
        def eligible(token):
            return token.is_string() or token.is_expr()

        def consolidate(start, end):
            if end == start + 1:
                token = tokens[start]
            else:
                # Generate a new Expression token that combines the strings and expressions into
                # a Python f'...' string.
                buffer = ["(f'''"]
                t = start
                while t < end:
                    token = tokens[t]
                    t += 1
                    if token.is_string():
                        buffer.append(token.value())
                    else:
                        buffer.extend(['{', token.source(), '}'])
                buffer.append("''')")
                token = Expression(''.join(buffer), 0, False, self.env.namespace)
            return token

        consolidated = []
        n = len(tokens)
        start = 0
        while start < n:
            while start < n and not eligible(tokens[start]):
                consolidated.append(tokens[start])
                start += 1
            end = start + 1
            while end < n and eligible(tokens[end]) and tokens[end].adjacent_to_previous:
                end += 1
            if start < n:
                consolidated.append(consolidate(start, end))
            start = end
        return consolidated

# ----------------------------------------------------------------------------------------------------------------------

# Parsing

# Grammar:
#
#     command:
#             assignment
#             pipeline
#    
#     assignment:
#             var = [ pipeline ]
#             var = expr
#             var = str
#    
#     pipeline:
#             op_sequence
#
#     op_sequence:
#             op_args | op_sequence
#             op_args
#    
#     op_args:
#             op arg*
#             expr
#    
#     op:
#             str
#             @
#             !
#             !!
#    
#     arg:
#             expr
#             str
#             [ pipeline ]
#    
#     var: str
#
#     expr: Expression
#
#     str: String


class Parser:

    def __init__(self, text, main):
        self.text = text
        self.env = main.env
        self.op_modules = main.op_modules
        self.tokens = Lexer(self.env, text).tokens()
        self.t = 0
        self.token = None  # The current token
        # For use by tab completer
        self.current_op_name = None
        self.current_op_flags = None

    def parse(self):
        return self.command()

    def command(self):
        if self.next_token(String, Assign):
            return self.assignment(self.token.value())
        else:
            return self.pipeline()

    def assignment(self, var):
        self.next_token(Assign)
        if self.next_token(Begin):
            op = self.create_assignment(var, pipeline=(self.pipeline()))
            self.next_token(End)
        elif self.next_token(String):
            op = self.create_assignment(var, string=(self.token.value()))
        elif self.next_token(Expression):
            op = self.create_assignment(var, function=(self.token.value()))
        else:
            self.next_token()
            raise UnexpectedTokenError(self.token, 'Unexpected token type.')
        return op

    def pipeline(self):
        op_sequence = Parser.ensure_sequence(self.op_sequence())
        op_sequence.reverse()
        pipeline = marcel.core.Pipeline()
        for op_args in op_sequence:
            pipeline.append(op_args)
        return pipeline

    # Accumulates ops in REVERSE order, to avoid list prepend.
    # Top-level caller needs to reverse the result..
    def op_sequence(self):
        self.current_op_name = None
        self.current_op_flags = None
        op_args = self.op_args()
        if self.next_token(Pipe):
            op_sequence = Parser.ensure_sequence(self.op_sequence())
            op_sequence.append(op_args)
            return op_sequence
        else:
            return op_args

    def op_args(self):
        if self.next_token(Expression):
            return self.create_map(self.token)
        else:
            op_token = self.op()
            args = []
            arg = self.arg()
            while arg is not None:
                args.append(arg)
                arg = self.arg()
            op = self.create_op(op_token, args)
            self.current_op_name = op.op_name()
            return op

    def op(self):
        if self.next_token(String) or self.next_token(Fork) or self.next_token(Run):
            return self.token
        elif self.next_token():
            raise UnexpectedTokenError(self.token, f'Unexpected token type: {self.token}')
        else:
            raise PrematureEndError()

    def arg(self):
        if self.next_token(Begin):
            pipeline = self.pipeline()
            self.next_token(End)
            return pipeline
        elif self.next_token(String) or self.next_token(Expression):
            return self.token.value()
        else:
            return None

    # Returns True if a qualifying token was found, and sets self.token to it.
    # Returns False if a qualifying token was not found, and leaves self.token unchanged.
    def next_token(self, *expected_token_types):
        n = len(expected_token_types)
        if self.t + n <= len(self.tokens):
            for i in range(n):
                if type(self.tokens[self.t + i]) is not expected_token_types[i]:
                    return False
            if self.t < len(self.tokens):
                self.token = self.tokens[self.t]
                self.t += 1
                return True
        return False

    @staticmethod
    def raise_unexpected_token_error(token, message):
        raise UnexpectedTokenError(token, message)

    def create_op(self, op_token, args):
        op = self.create_op_builtin(op_token, args)
        if op is None:
            op = self.create_op_variable(op_token, args)
        if op is None:
            op = self.create_op_executable(op_token, args)
        if op is None:
            raise UnknownOpError(op_token.value())
        return op

    def create_op_builtin(self, op_token, args):
        op = None
        op_name = op_token.op_name()
        try:
            op_module = self.op_modules[op_name]
            op = op_module.create_op()
            # Both ! and !! map to the run op.
            if op_name == 'run':
                # !: Expect a command number
                # !!: Don't expect a command number, run the previous command
                # else: 'run' was entered
                op.expected_args = (1 if op_token.value() == '!' else
                                    0 if op_token.value() == '!!' else None)
            args_parser = op_module.args_parser()
            self.current_op_flags = args_parser.flags()
            args_parser.parse(args, op)
        except KeyError:
            pass
        return op

    def create_op_variable(self, op_token, args):
        # TODO: There shouldn't be any args
        op = None
        var = op_token.value()
        value = self.env.getvar(var)
        if value:
            op_module = self.op_modules['runpipeline']
            op = op_module.create_op()
            op.var = var
        return op

    def create_op_executable(self, op_token, args):
        op = None
        name = op_token.value()
        if marcel.util.is_executable(name):
            op = marcel.opmodule.create_op(self.env, 'bash', *([name] + args))
        return op

    def create_assignment(self, var, string=None, pipeline=None, function=None):
        assign_module = self.op_modules['assign']
        assert assign_module is not None
        op = assign_module.create_op()
        op.var = var
        if string is not None:
            op.string = string
        if pipeline is not None:
            op.pipeline = pipeline
        if function is not None:
            op.function = function
        pipeline = marcel.core.Pipeline()
        pipeline.append(op)
        return pipeline

    def create_map(self, expr):
        assert type(expr) is Expression
        return marcel.opmodule.create_op(self.env, 'map', expr.value())

    @staticmethod
    def ensure_sequence(x):
        if not marcel.util.is_sequence_except_string(x):
            x = [x]
        return x
