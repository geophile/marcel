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

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.function
import marcel.opmodule
import marcel.util


# ----------------------------------------------------------------------------------------------------------------------

# Parsing errors

class SyntaxError(marcel.exception.KillCommandException):
    SNIPPET_SIZE = 10

    def __init__(self, token, message):
        super().__init__(message)
        self.token = token
        self.message = message

    def __str__(self):
        if self.token is None:
            return 'Premature end of input'
        else:
            token_start = self.token.start
            token_text = self.token.text
            snippet_start = max(token_start - SyntaxError.SNIPPET_SIZE, 0)
            snippet_end = max(token_start + SyntaxError.SNIPPET_SIZE + 1, len(token_text))
            snippet = token_text[snippet_start:snippet_end]
            if snippet_start > 0:
                snippet = '...' + snippet
            return f'Parsing error at position {token_start - snippet_start} of "{snippet}...": {self.message}'


class PrematureEndError(SyntaxError):

    def __init__(self, token=None):
        super().__init__(token, "Premature end of input")


class UnknownOpError(marcel.exception.KillCommandException):

    def __init__(self, op_name):
        super().__init__(op_name)
        self.op_name = op_name

    def __str__(self):
        return f'Unknown command: {self.op_name}'


class ParseError(marcel.exception.KillCommandException):

    def __init__(self, message):
        super().__init__(message)


class EmptyCommand(marcel.exception.KillCommandException):

    def __init__(self):
        super().__init__(None)


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

    def peek_char(self, n=1):
        c = None
        if self.end + n <= len(self.text):
            c = self.text[self.end:self.end + n]
        return c

    def next_char(self):
        c = None
        if self.end < len(self.text):
            c = self.text[self.end]
            self.end += 1
        return c

    def remaining(self):
        return len(self.text) - self.end

    def raw(self):
        return self.text[self.start:self.end]


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
    COMMENT = '#'
    COMMA = ','
    COLON = ':'
    ARROW = '>'
    ARROW_2 = '>>'
    LONG_ARROW_2 = '->>'
    STRING_TERMINATING = [OPEN, CLOSE, PIPE, BEGIN, END, ASSIGN, COMMENT, COMMA, COLON, ARROW, ARROW_2]

    def __init__(self, text, position, adjacent_to_previous):
        super().__init__(text, position)
        self.adjacent_to_previous = adjacent_to_previous

    def value(self, parser):
        return None

    def is_string(self):
        return False

    def is_op(self):
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

    def is_comma(self):
        return False

    def is_colon(self):
        return False

    def is_arrow(self):
        return False

    def is_lexer_failure(self):
        return False

    def op_name(self):
        return None

    def is_followed_by_whitespace(self):
        return self.end < len(self.text) and self.text[self.end].isspace()


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

    def value(self, parser):
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
                raise LexerException(self, "Not a python string")
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

    def __init__(self, text, position, adjacent_to_previous):
        super().__init__(text, position, adjacent_to_previous)
        self._source = None
        self._function = None
        self.scan()

    def value(self, parser):
        try:
            if self._function is None:
                source = self.source()
                globals = parser.env.namespace
                split = source.split()
                if len(split) == 0:
                    raise marcel.exception.KillCommandException(f'Empty function definition.')
                if split[0] in ('lambda', 'lambda:'):
                    function = eval(source, globals)
                else:
                    try:
                        function = eval('lambda ' + source, globals)
                        source = 'lambda ' + source
                    except Exception:
                        try:
                            function = eval('lambda: ' + source, globals)
                            source = 'lambda: ' + source
                        except Exception:
                            raise marcel.exception.KillCommandException(f'Invalid function syntax: {source}')
                self._function = marcel.function.SourceFunction(function=function, source=source)
            return self._function
        except Exception as e:
            raise SyntaxError(self, f'Error in function: {e}')

    def is_expr(self):
        return True

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
            raise LexerException(self, 'Malformed Python expression')


class String(Token):

    def __init__(self, text, position=None, adjacent_to_previous=False):
        super().__init__(text, 0 if position is None else position, adjacent_to_previous)
        if position is None:
            # Text is fine as is.
            self.string = text
            self.end = len(text)
        else:
            # Text is from the input being parsed. Scan it to deal with escapes and quotes.
            self.string = None
            self.scan()

    def value(self, parser):
        return self.string

    def is_string(self):
        return True

    def op_name(self):
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
                    raise LexerException(self, 'Malformed string')
            else:
                chars.append(c)
        self.string = ''.join(chars)


class Op(String):

    def __init__(self, text, position=None, adjacent_to_previous=False):
        super().__init__(text, 0 if position is None else position, adjacent_to_previous)

    # Op is a subclass of String, so that the implementation of String can be inherited.
    # But for classification of tokens, they should be considered as separate things,
    # so is_string() is overridden to return False.
    def is_string(self):
        return False

    def is_op(self):
        return True

    def op_name(self):
        return self.string


class Run(Token):

    def __init__(self, text, position, adjacent_to_previous):
        super().__init__(text, position, adjacent_to_previous)
        self.symbol = None
        self.scan()  # Sets self.symbol

    def value(self, parser):
        return self.symbol

    def is_bang(self):
        return True

    def is_op(self):
        return True

    def op_name(self):
        return 'run'

    def scan(self):
        c = self.next_char()
        assert c == Token.BANG
        c = self.peek_char()
        if c == Token.BANG:
            self.next_char()
            self.symbol = '!!'
        else:
            self.symbol = '!'


class Symbol(Token):

    def __init__(self, text, position, adjacent_to_previous, symbol):
        super().__init__(text, position, adjacent_to_previous)
        self.symbol = symbol
        self.end += 1

    def value(self, parser):
        return self.symbol


class Pipe(Symbol):

    def __init__(self, text, position, adjacent_to_previous):
        super().__init__(text, position, adjacent_to_previous, Token.PIPE)

    def is_pipe(self):
        return True


class Fork(Symbol):

    def __init__(self, text, position, adjacent_to_previous):
        super().__init__(text, position, adjacent_to_previous, Token.FORK)

    def is_fork(self):
        return True

    def is_op(self):
        return True

    def op_name(self):
        return 'fork'


class Begin(Symbol):

    def __init__(self, text, position, adjacent_to_previous):
        super().__init__(text, position, adjacent_to_previous, Token.BEGIN)

    def is_begin(self):
        return True


class End(Symbol):

    def __init__(self, text, position, adjacent_to_previous):
        super().__init__(text, position, adjacent_to_previous, Token.END)

    def is_end(self):
        return True


class Assign(Symbol):

    def __init__(self, text, position, adjacent_to_previous):
        super().__init__(text, position, adjacent_to_previous, Token.ASSIGN)

    def is_assign(self):
        return True

    def op_name(self):
        return 'assign'


class Comma(Symbol):

    def __init__(self, text, position, adjacent_to_previous):
        super().__init__(text, position, adjacent_to_previous, Token.COMMA)

    def is_comma(self):
        return True


class Colon(Symbol):

    def __init__(self, text, position, adjacent_to_previous):
        super().__init__(text, position, adjacent_to_previous, Token.COLON)

    def is_colon(self):
        return True


class Arrow(Symbol):

    def __init__(self, text, position, adjacent_to_previous, symbol):
        super().__init__(text, position, adjacent_to_previous, symbol)
        assert symbol in (Token.ARROW, Token.ARROW_2)
        self.end += len(symbol) - 1  # Symbol.__init__ already added one

    def is_arrow(self):
        return True

    def is_append(self):
        return self.symbol == Token.ARROW_2


class ImpliedMap(Token):

    def __init__(self):
        super().__init__(None, None, False)

    def op_name(self):
        return 'map'


class LexerFailure(Token):

    def __init__(self, exception):
        super().__init__(None, None, None)
        self.exception = exception

    def is_lexer_failure(self):
        return True


# ----------------------------------------------------------------------------------------------------------------------

# Lexing


class LexerException(marcel.exception.KillCommandException):

    def __init__(self, token, message):
        super().__init__(f'{token.text[token.start:token.end]}: {message}')


class Lexer(Source):

    def __init__(self, main, text):
        super().__init__(text)
        self.main = main

    def tokens(self):
        tokens = []
        try:
            token = self.next_token()
            while token is not None:
                tokens.append(token)
                token = self.next_token()
        except LexerException as e:
            tokens.append(LexerFailure(e))
        return self.consolidate_adjacent(tokens)

    def next_token(self):
        token = None
        skipped = self.skip_whitespace()
        c = self.peek_char()
        if c is not None:
            adjacent_to_previous = self.end > 0 and skipped == 0
            if self.match(c, Token.OPEN):
                token = Expression(self.text, self.end, adjacent_to_previous)
            elif self.match(c, Token.CLOSE):
                raise ParseError('Unmatched )')
            elif self.match(c, Token.PIPE):
                token = Pipe(self.text, self.end, adjacent_to_previous)
            elif self.match(c, Token.BEGIN):
                token = Begin(self.text, self.end, adjacent_to_previous)
            elif self.match(c, Token.END):
                token = End(self.text, self.end, adjacent_to_previous)
            elif self.match(c, Token.FORK):
                token = Fork(self.text, self.end, adjacent_to_previous)
            elif self.match(c, Token.BANG):
                token = Run(self.text, self.end, adjacent_to_previous)
            elif self.match(c, Token.ASSIGN):
                token = Assign(self.text, self.end, adjacent_to_previous)
            elif self.match(c, Token.COMMA):
                token = Comma(self.text, self.end, adjacent_to_previous)
            elif self.match(c, Token.COLON):
                token = Colon(self.text, self.end, adjacent_to_previous)
            elif self.match(c, Token.COMMENT):
                return None  # Ignore the rest of the line
            elif self.match(c, Token.ARROW_2):
                token = Arrow(self.text, self.end, adjacent_to_previous, Token.ARROW_2)
            elif self.match(c, Token.ARROW):
                token = Arrow(self.text, self.end, adjacent_to_previous, Token.ARROW)
            else:
                token = String(self.text, self.end, adjacent_to_previous)
                if token.string in self.main.op_modules:
                    token = Op(self.text, self.end, adjacent_to_previous)
            self.end = token.end
        return token

    def match(self, c, symbol):
        return self.peek_char(len(symbol)) == symbol

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
                        buffer.append(token.value(None))
                    else:
                        buffer.extend(['{', token.source(), '}'])
                buffer.append("''')")
                token = Expression(''.join(buffer), 0, False)
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
#             var = arg
#    
#     pipeline:
#             var store var
#             var > [op_sequence [store var]]
#             op_sequence [store var]
#             store var
#
#     op_sequence:
#             op_args | op_sequence
#             op_args
#
#     store:
#             >
#             >>
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
#             begin [vars :] pipeline end
#
#     vars:
#             vars, var
#             var
#
#     var: str
#
#     expr: Expression
#
#     str: String
#
#     begin: [
#
#     end: ]
#
# Notes:
#
# - An op can be a str, i.e., the name of an operator. It can also be a var, but that's a str
#   also.


class TabCompletionContext:
    COMPLETE_OP = 'COMPLETE_OP'
    COMPLETE_ARG = 'COMPLETE_ARG'
    COMPLETE_DISABLED = 'COMPLETE_DISABLED'

    def __init__(self):
        self._complete = TabCompletionContext.COMPLETE_OP
        self._op_token = None
        self._op = None
        self._flags = None

    def __repr__(self):
        return ('op' if self._complete == TabCompletionContext.COMPLETE_OP else
                f'arg({self._op_token})' if self._complete == TabCompletionContext.COMPLETE_ARG else
                f'disabled')

    def complete_op(self):
        self._complete = TabCompletionContext.COMPLETE_OP
        self._op_token = None

    def complete_arg(self, op_token):
        self._complete = TabCompletionContext.COMPLETE_ARG
        self._op_token = op_token

    def complete_disabled(self):
        self._complete = TabCompletionContext.COMPLETE_DISABLED
        self._op_token = None

    def is_complete_op(self):
        return self._complete is TabCompletionContext.COMPLETE_OP

    def is_complete_arg(self):
        return self._complete is TabCompletionContext.COMPLETE_ARG

    def is_complete_disabled(self):
        return self._complete is TabCompletionContext.COMPLETE_DISABLED

    def set_op(self, op, flags):
        self._op = op
        self._flags = flags

    def op(self):
        return self._op

    def flags(self):
        return self._flags


class Parser:

    def __init__(self, text, main):
        self.text = text
        self.env = main.env
        self.op_modules = main.op_modules
        self.tokens = Lexer(main, text).tokens()
        self.t = 0
        self.token = None  # The current token
        self.current_pipelines = marcel.util.Stack()
        self.tab_completion_context = TabCompletionContext()

    def parse(self):
        if len(self.tokens) == 0:
            raise EmptyCommand()
        return self.command()

    def command(self):
        if self.next_token(String, Assign):
            self.tab_completion_context.complete_disabled()
            command = self.assignment(self.token.value(self))
        else:
            self.tab_completion_context.complete_op()
            command = self.pipeline(None)
        if not self.at_end():
            excess = ', '.join([str(t) for t in self.tokens[self.t:]])
            raise ParseError(f'{command} followed by excess tokens: {excess}')
        return command

    def assignment(self, var):
        self.next_token(Assign)
        arg = self.arg()
        if isinstance(arg, Token):
            value = arg.value(self)
        elif type(arg) is marcel.core.Pipeline:
            value = arg
        elif arg is None:
            raise SyntaxError(self.token, 'Unexpected token type.')
        else:
            assert False, arg
        op = self.create_assignment(var, value)
        return op

    def pipeline(self, parameters):
        pipeline = marcel.core.Pipeline()
        pipeline.set_parameters(parameters)
        self.current_pipelines.push(pipeline)
        if self.next_token(Op, Arrow):
            op_token = self.token
            self.tab_completion_context.complete_disabled()
            found_arrow = self.next_token(Arrow)
            assert found_arrow
            arrow_token = self.token
            if self.pipeline_end():
                # op >
                raise SyntaxError(self.token, f'A variable must precede {arrow_token.value(self)}, '
                                              f'not an operator ({self.token.op_name()})')
            elif self.pipeline_end(1):
                if self.next_token(String):
                    # op > var
                    op = (op_token, [])
                    store_op = self.store_op(self.token, arrow_token.is_append())
                    op_sequence = [op, store_op]
                else:
                    raise SyntaxError(arrow_token, f'Incorrect use of {arrow_token.value(self)}')
            else:
                raise SyntaxError(arrow_token, f'Incorrect use of {arrow_token.value(self)}')
        elif self.next_token(String, Arrow):
            self.tab_completion_context.complete_disabled()
            load_op = self.load_op(self.token)
            found_arrow = self.next_token(Arrow)
            assert found_arrow
            self.tab_completion_context.complete_disabled()
            arrow_token = self.token
            if self.pipeline_end():
                # var >
                if arrow_token.is_append():
                    raise SyntaxError(arrow_token, 'Append not permitted here.')
                op_sequence = [load_op]
            elif self.pipeline_end(1):
                if self.next_token(Op):
                    # var > op
                    if arrow_token.is_append():
                        raise SyntaxError(arrow_token, 'Append not permitted here.')
                    op = (self.token, [])
                    op_sequence = [load_op, op]
                elif self.next_token(String):
                    # var > var
                    store_op = self.store_op(self.token, arrow_token.is_append())
                    op_sequence = [load_op, store_op]
                elif self.next_token(Expression):
                    # map is implied
                    if arrow_token.is_append():
                        raise SyntaxError(arrow_token, 'Append not permitted here.')
                    map_op = self.map_op(self.token)
                    op_sequence = [load_op, map_op]
                else:
                    assert False
            else:
                op_sequence = [load_op] + self.op_sequence()
                if self.next_token(Arrow, String):
                    # var > op_sequence > var
                    arrow_token = self.token
                    found_string = self.next_token(String)
                    assert found_string
                    store_op = self.store_op(self.token, arrow_token.is_append())
                    op_sequence.append(store_op)
                else:
                    # var > op_sequence
                    if arrow_token.is_append():
                        raise SyntaxError(arrow_token, 'Append not permitted here.')
        elif self.next_token(Arrow, String):
            self.tab_completion_context.complete_disabled()
            # > var
            arrow_token = self.token
            found_string = self.next_token(String)
            assert found_string
            store_op = self.store_op(self.token, arrow_token.is_append())
            op_sequence = [store_op]
        else:
            op_sequence = self.op_sequence()
            if self.next_token(Arrow, String):
                # op_sequence > var
                arrow_token = self.token
                found_string = self.next_token(String)
                assert found_string
                store_op = self.store_op(self.token, arrow_token.is_append())
                op_sequence.append(store_op)
            # else:  op_sequence is OK as is
        for op_args in op_sequence:
            # op_args is (op_token, list of arg tokens)
            pipeline.append(self.create_op(*op_args))
        self.current_pipelines.pop()
        return pipeline

    @staticmethod
    def load_op(var):
        return Op('load'), [var]

    @staticmethod
    def store_op(var, append):
        return Op('store'), ['--append', var] if append else [var]

    @staticmethod
    def map_op(expr):
        return Op('map'), [expr]

    def op_sequence(self):
        op_args = [self.op_args()]
        if self.next_token(Pipe):
            self.tab_completion_context.complete_disabled()
            return op_args + self.op_sequence()
        else:
            return op_args

    # Returns (op name, list of arg tokens)
    def op_args(self):
        self.tab_completion_context.complete_op()
        if self.next_token(Expression):
            op_args = (Op('map'), [self.token])
        else:
            op_token = self.op()
            arg_tokens = []
            if op_token.is_followed_by_whitespace():
                self.tab_completion_context.complete_arg(op_token)
            if not self.at_end():
                arg_token = self.arg()
                while arg_token is not None:
                    arg_tokens.append(arg_token)
                    arg_token = self.arg()
            op_args = (op_token, arg_tokens)
        return op_args

    def op(self):
        if self.next_token(Op) or self.next_token(String) or self.next_token(Fork) or self.next_token(Run):
            return self.token
        else:
            raise PrematureEndError(self.token)

    def arg(self):
        if self.next_token(Begin):
            self.tab_completion_context.complete_disabled()
            # If the next tokens are var comma, or var colon, then we have
            # pipeline variables being declared.
            if self.next_token(String, Comma) or self.next_token(String, Colon):
                pipeline_parameters = self.vars()
            else:
                pipeline_parameters = None
            pipeline = self.pipeline(pipeline_parameters)
            if self.next_token(End):
                return pipeline
            else:
                raise PrematureEndError(self.token)
        elif self.next_token(String) or self.next_token(Op) or self.next_token(Expression):
            return self.token
        else:
            return None

    def vars(self):
        vars = []
        while self.token.is_string():
            vars.append(self.token.value(self))
            if self.next_token(Comma):
                if not self.next_token(String):
                    self.next_token()
                    raise SyntaxError(self.token, f'Expected a var, found {self.token}')
            else:
                self.next_token()  # Should be string or colon
        # Shouldn't have called vars() unless the token (on entry) was a string.
        assert len(vars) > 0
        if not self.token.is_colon():
            raise SyntaxError(self.token, f'Expected comma or colon, found {self.token}')
        return vars

    # Returns True if a qualifying token was found, and sets self.token to it.
    # Returns False if a qualifying token was not found, and leaves self.token unchanged.
    def next_token(self, *expected_token_types):
        if self.t < len(self.tokens) and self.tokens[self.t].is_lexer_failure():
            raise self.tokens[self.t].exception
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

    # Does token t+n indicate the end of a pipeline?
    def pipeline_end(self, n=0):
        p = self.t + n
        return p == len(self.tokens) or self.tokens[p].is_end()

    def at_end(self):
        return self.t >= len(self.tokens)

    @staticmethod
    def raise_unexpected_token_error(token, message):
        raise SyntaxError(token, message)

    def create_op(self, op_token, arg_tokens):
        op = self.create_op_builtin(op_token, arg_tokens)
        if op is None:
            op = self.create_op_executable(op_token, arg_tokens)
        if op is None:
            op = self.create_op_variable(op_token, arg_tokens)
        return op

    def create_op_builtin(self, op_token, arg_tokens):
        op = None
        if op_token.is_op():
            op_name = op_token.op_name()
            op_module = self.op_modules[op_name]
            op = op_module.create_op()
            # Both ! and !! map to the run op.
            if op_name == 'run':
                # !: Expect a command number
                # !!: Don't expect a command number, run the previous command
                # else: 'run' was entered
                op.expected_args = (1 if op_token.value(self) == '!' else
                                    0 if op_token.value(self) == '!!' else None)
            args = []
            if op_name == 'bash':
                for x in arg_tokens:
                    args.append(x.raw() if type(x) is String else
                                x.value(self) if isinstance(x, Token) else
                                x)
            else:
                for x in arg_tokens:
                    args.append(x.value(self) if isinstance(x, Token) else x)
                self.tab_completion_context.set_op(op, op_module.args_parser().flags())
            op_module.args_parser().parse(args, op)
        return op

    def create_op_variable(self, op_token, arg_tokens):
        var = op_token.value(self)
        op_module = self.op_modules['runpipeline']
        op = op_module.create_op()
        op.var = var
        if len(arg_tokens) > 0:
            pipeline_args = []
            for token in arg_tokens:
                pipeline_args.append(token
                                     if type(token) is marcel.core.Pipeline else
                                     token.value(self))
            args, kwargs = marcel.argsparser.PipelineArgsParser(var).parse_pipeline_args(pipeline_args)
            op.set_pipeline_args(args, kwargs)
        return op

    def create_op_executable(self, op_token, arg_tokens):
        op = None
        name = op_token.value(self)
        if marcel.util.is_executable(name):
            args = [name]
            for x in arg_tokens:
                args.append(x.raw() if type(x) is String else
                            x.value(self) if isinstance(x, Token) else
                            x)
            op = marcel.opmodule.create_op(self.env, 'bash', *args)
        return op

    def create_assignment(self, var, value):
        assign_module = self.op_modules['assign']
        assert assign_module is not None
        op = assign_module.create_op()
        op.var = var
        if callable(value):
            op.function = value
        elif type(value) is marcel.core.Pipeline:
            op.pipeline = value
        elif type(value) is str:
            op.string = value
        else:
            assert False, value
        pipeline = marcel.core.Pipeline()
        pipeline.append(op)
        return pipeline
