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
            token_start = self.token.position
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
        return self.text[self.start:self.end]

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

    def __init__(self, text, position):
        super().__init__(text, position)

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

    def __init__(self, text, position):
        super().__init__(text, position)
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

    def __init__(self, text, position):
        super().__init__(text, position)
        self.scan()

    def is_expr(self):
        return True

    def value(self):
        return self.text[self.start + 1:self.end - 1]

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
                self.end = PythonString(self.text, self.end - 1).end
        if self.text[self.end - 1] != Token.CLOSE:
            raise marcel.exception.KillCommandException(
                f'Malformed Python expression {self.text[self.start:self.end]}')


class String(Token):

    def __init__(self, text, position):
        super().__init__(text, position)
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

    def __init__(self, text, position):
        super().__init__(text, position)
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

    def __init__(self, text, position, symbol):
        super().__init__(text, position)
        self.symbol = symbol
        self.end += 1

    def value(self):
        return self.symbol


class Pipe(OneCharSymbol):

    def __init__(self, text, position):
        super().__init__(text, position, Token.PIPE)

    def is_pipe(self):
        return True


class Fork(OneCharSymbol):

    def __init__(self, text, position):
        super().__init__(text, position, Token.FORK)

    def is_fork(self):
        return True

    def op_name(self):
        return 'fork'


class Begin(OneCharSymbol):

    def __init__(self, text, position):
        super().__init__(text, position, Token.BEGIN)

    def is_begin(self):
        return True


class End(OneCharSymbol):

    def __init__(self, text, position):
        super().__init__(text, position, Token.END)

    def is_end(self):
        return True


class Assign(OneCharSymbol):

    def __init__(self, text, position):
        super().__init__(text, position, Token.ASSIGN)

    def is_assign(self):
        return True

    def op_name(self):
        return 'assign'


class ImpliedMap(Token):

    def __init__(self):
        super().__init__(None, None)

    def op_name(self):
        return 'map'


# ----------------------------------------------------------------------------------------------------------------------

# Parsing

class ParseState(Enum):
    START = auto()
    DONE = auto()
    END = auto()
    OP = auto()
    ARGS = auto()


class InProgress:

    def __init__(self):
        self.pipeline = marcel.core.Pipeline()
        self.op_token = None
        self.args = []

    def reset_op(self):
        self.op_token = None
        self.args.clear()


# ----------------------------------------------------------------------------------------------------------------------

# Lexing


class Lexer(Source):

    def __init__(self, text):
        super().__init__(text)

    def tokens(self):
        tokens = []
        token = self.next_token()
        while token is not None:
            tokens.append(token)
            token = self.next_token()
        return tokens

    def next_token(self):
        token = None
        self.skip_whitespace()
        c = self.peek_char()
        if c is not None:
            if c == Token.OPEN:
                token = Expression(self.text, self.end)
            elif c == Token.CLOSE:
                raise ParseError('Unmatched )')
            elif c == Token.PIPE:
                token = Pipe(self.text, self.end)
            elif c == Token.BEGIN:
                token = Begin(self.text, self.end)
            elif c == Token.END:
                token = End(self.text, self.end)
            elif c == Token.FORK:
                token = Fork(self.text, self.end)
            elif c == Token.BANG:
                token = Run(self.text, self.end)
            elif c == Token.ASSIGN:
                token = Assign(self.text, self.end)
            else:
                token = String(self.text, self.end)
            self.end = token.end
        return token

    def skip_whitespace(self):
        c = self.peek_char()
        while c is not None and c.isspace():
            self.next_char()
            c = self.peek_char()

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
        self.tokens = Lexer(text).tokens()
        self.t = 0
        self.token = None  # The current token
        # For use by tab completer
        self.current_op_name = None

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
            value = self.pipeline()
            op = self.create_assignment(var, pipeline=value)
            self.next_token(End)
        elif self.next_token(String):
            value = self.token.value()
            op = self.create_assignment(var, string=value)
        elif self.next_token(Expression):
            value = self.token.value()
            op = self.create_assignment(var, source=value)
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
            self.current_op_name = op_token.value()
            args = []
            arg = self.arg()
            while arg is not None:
                args.append(arg)
                arg = self.arg()
            op = self.create_op(op_token, args)
            return op

    def op(self):
        if self.next_token(String) or self.next_token(Fork) or self.next_token(Run):
            return self.token
        elif self.next_token():
            raise UnexpectedTokenError(self.token, 'Unexpected token type.')
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
            arg_parser = op_module.arg_parser()
            arg_parser.parse_args(args, namespace=op)
        except KeyError:
            pass
        return op

    def create_op_variable(self, op_token, args):
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
            op_module = self.op_modules['bash']
            op = op_module.create_op()
            args = [name] + args
            arg_parser = op_module.arg_parser()
            arg_parser.parse_args(args, namespace=op)
        return op

    def create_assignment(self, var, string=None, pipeline=None, source=None):
        assign_module = self.op_modules['assign']
        assert assign_module is not None
        op = assign_module.create_op()
        op.var = var
        if string is not None:
            op.string = string
        if pipeline is not None:
            op.pipeline = pipeline
        if source is not None:
            op.source = source
        pipeline = marcel.core.Pipeline()
        pipeline.append(op)
        return pipeline

    def create_map(self, expr):
        assert type(expr) is Expression
        map_module = self.op_modules['map']
        assert map_module is not None
        op = map_module.create_op()
        arg_parser = map_module.arg_parser()
        arg_parser.parse_args([expr.value()], namespace=op)
        return op

    @staticmethod
    def ensure_sequence(x):
        if not marcel.util.is_sequence_except_string(x):
            x = [x]
        return x
