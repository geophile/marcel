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
        buffer = [self.__class__.__name__, '(']
        if self.text is not None:
            if self.start is not None and self.end is not None:
                buffer.append('[')
                buffer.append(str(self.start))
                buffer.append(':')
                buffer.append(str(self.end))
                buffer.append(']')
                buffer.append(self.text[self.start:self.end])
            else:
                buffer.append(self.text)
        buffer.append(')')
        return ''.join(buffer)

    def more(self):
        return self.end < len(self.text)

    def peek(self, n=1):
        start = self.end
        end = self.end + n
        return self.text[start:end] if end <= len(self.text) else None

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

    def mark(self):
        return self.text, self.start, self.end

    def reset(self, mark):
        text, start, end = mark
        assert self.text == text
        self.start, self.end = start, end


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
    REMOTE = '@'
    BEGIN = '(|'
    END = '|)'
    ASSIGN = '='
    COMMENT = '#'
    COMMA = ','
    COLON = ':'
    REDIRECT_FILE = '>'
    REDIRECT_FILE_APPEND = '>>'
    REDIRECT_VAR = '>$'
    REDIRECT_VAR_APPEND = '>>$'
    STRING_TERMINATING = [
        OPEN,
        CLOSE,
        PIPE,
        BEGIN,
        END,
        ASSIGN,
        COMMENT,
        COMMA,
        COLON,
        REDIRECT_FILE,
        REDIRECT_FILE_APPEND,
        REDIRECT_VAR,
        REDIRECT_VAR_APPEND
    ]
    SHELL_STRING_TERMINATING = [
        OPEN,
        CLOSE,
        PIPE,
        REDIRECT_FILE,
        REDIRECT_FILE_APPEND,
        REDIRECT_VAR,
        REDIRECT_VAR_APPEND
    ]

    def __init__(self, parser, text, position):
        super().__init__(text, position)
        self.parser = parser
        self.adjacent_to_next = False

    def value(self):
        return None

    def is_string(self):
        return False

    # Does this token represent a builtin op?
    def is_op(self):
        return False

    def is_remote(self):
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

    def mark_adjacent_to_next(self):
        self.adjacent_to_next = True


# PythonString isn't a top-level token that appears on a command line. An Expression is defined as
# everything in between a top-level ( and the matching ). Everything delimited by those parens is
# simply passed to Python's eval. However, in order to do the matching, any parens inside a Python
# string (which could be part of the Expression) must be ignored.
#
# Python string literals are specified here:
# https://docs.python.org/3/reference/lexical_analysis.html#string-and-bytes-literals.
class PythonString(Token):

    def __init__(self, parser, text, position):
        super().__init__(parser, text, position)
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

    def __init__(self, parser, text, position):
        super().__init__(parser, text, position)
        self._source = None
        self._function = None
        self.scan()

    def value(self):
        try:
            if self._function is None:
                source = self.source()
                globals = self.parser.env.namespace
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
                self.end = PythonString(self.parser, self.text, self.end - 1).end
        if self.text[self.end - 1] != Token.CLOSE:
            raise LexerException(self, 'Malformed Python expression')


class String(Token):

    def __init__(self, parser, text, position, scan_termination):
        assert position >= 0
        super().__init__(parser, text, position)
        self.string = None
        self.scan(scan_termination)
        # op_modules is a dict, name -> OpModule
        self.op_name = self.string if self.string in parser.op_modules else None

    def value(self):
        return self.string

    def is_string(self):
        return True

    def is_op(self):
        return self.op_name is not None

    def scan(self, scan_termination):
        quote = None
        chars = []
        while True:
            c = self.next_char()
            if c is None:
                break
            elif c.isspace() or c in scan_termination:
                if quote is None:
                    # c is part of the next token
                    self.end -= 1
                    break
                else:
                    # quoted whitespace or character that would otherwise terminate the string
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


class MarcelString(String):

    def __init__(self, parser, text, position):
        super().__init__(parser, text, position, Token.STRING_TERMINATING)


class ShellString(String):

    def __init__(self, parser, text, position):
        super().__init__(parser, text, position, Token.SHELL_STRING_TERMINATING)


class ConstructedString(String):

    def __init__(self, parser, text):
        super().__init__(parser, text, 0, '')
        self.text = text
        self.end = len(text)

    def scan(self, scan_termination):
        self.string = self.text


class Run(Token):

    def __init__(self, parser, text, position):
        super().__init__(parser, text, position)
        self.symbol = None
        self.scan()  # Sets self.symbol

    def value(self):
        return self.symbol

    def is_bang(self):
        return True

    def is_op(self):
        return True

    @property
    def op_name(self):
        return 'run'

    def scan(self):
        c = self.next_char()
        assert c == Token.BANG
        c = self.peek()
        if c == Token.BANG:
            self.next_char()
            self.symbol = '!!'
        else:
            self.symbol = '!'


class Symbol(Token):

    def __init__(self, parser, text, position, symbol):
        super().__init__(parser, text, position)
        self.symbol = symbol
        self.end += len(symbol)

    def value(self):
        return self.symbol


class Pipe(Symbol):

    def __init__(self, parser, text, position):
        super().__init__(parser, text, position, Token.PIPE)

    def is_pipe(self):
        return True


class Remote(Symbol):

    def __init__(self, parser, text, position):
        super().__init__(parser, text, position, Token.REMOTE)

    def is_remote(self):
        return True

    def is_op(self):
        return True

    @property
    def op_name(self):
        return 'remote'


class Begin(Symbol):

    def __init__(self, parser, text, position):
        super().__init__(parser, text, position, Token.BEGIN)

    def is_begin(self):
        return True


class End(Symbol):

    def __init__(self, parser, text, position):
        super().__init__(parser, text, position, Token.END)

    def is_end(self):
        return True


class Assign(Symbol):

    def __init__(self, parser, text, position):
        super().__init__(parser, text, position, Token.ASSIGN)

    def is_assign(self):
        return True

    def op_name(self):
        return 'assign'


class Comma(Symbol):

    def __init__(self, parser, text, position):
        super().__init__(parser, text, position, Token.COMMA)

    def is_comma(self):
        return True


class Colon(Symbol):

    def __init__(self, parser, text, position):
        super().__init__(parser, text, position, Token.COLON)

    def is_colon(self):
        return True


class Arrow(Symbol):

    def __init__(self, parser, text, position, symbol):
        super().__init__(parser, text, position, symbol)
        assert symbol in (Token.REDIRECT_VAR, Token.REDIRECT_VAR_APPEND,
                          Token.REDIRECT_FILE, Token.REDIRECT_FILE_APPEND)

    def is_arrow(self):
        return True

    def is_var(self):
        return self.symbol in (Token.REDIRECT_VAR, Token.REDIRECT_VAR_APPEND)

    def is_file(self):
        return self.symbol in (Token.REDIRECT_FILE, Token.REDIRECT_FILE_APPEND)

    def is_append(self):
        return self.symbol in (Token.REDIRECT_VAR_APPEND, Token.REDIRECT_FILE_APPEND)


class ImpliedMap(Token):

    def __init__(self):
        super().__init__(None, None, None)

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

    def __init__(self, parser, text):
        super().__init__(text)
        self.parser = parser

    def next_token(self):
        def consolidatable(token):
            return token.is_string() or token.is_expr()

        token = self.next_unconsolidated_token()
        adjacent_tokens = [token]
        while token and token.adjacent_to_next and consolidatable(token):
            # Don't consume the next token if it isn't going to be consollidated.
            mark = self.mark()
            token = self.next_unconsolidated_token()
            if consolidatable(token):
                adjacent_tokens.append(token)
            else:
                # token is not consolidatable, so loop condition will be false.
                self.reset(mark)
        n_adjacent = len(adjacent_tokens)
        consolidated = self.consolidate(adjacent_tokens) if n_adjacent > 1 else adjacent_tokens[0]
        return consolidated

    def consolidate(self, tokens):
        # Generate a new Expression token that combines the strings and expressions into
        # a Python f'...' string.
        buffer = ["(f'''"]
        for token in tokens:
            if token.is_string():
                buffer.append(token.value())
            elif token.is_expr():
                buffer.extend(['{', token.source(), '}'])
            else:
                assert False, token
        buffer.append("''')")
        token = Expression(self.parser, ''.join(buffer), 0)
        # print(f'{tokens} -> {token}')
        return token

    def next_unconsolidated_token(self):
        # These symbols have special significance during marcel parsing, but not bash:
        #     BEGIN
        #     END
        #     REMOTE
        #     ASSIGN
        #     COMMA
        #     COLON
        # So don't create tokens for them if we are doing marcel-mode parsing.
        marcel_mode = not self.parser.shell_op
        token = None
        self.skip_whitespace()
        if self.more():
            # BEGIN is (|, OPEN is (
            # END IS |), CLOSE is )
            # PIPE is |
            # So look for BEGIN and END before those other symbols.
            if marcel_mode and self.match(Token.BEGIN):
                token = Begin(self.parser, self.text, self.end)
            elif marcel_mode and self.match(Token.END):
                token = End(self.parser, self.text, self.end)
            elif self.match(Token.OPEN):
                token = Expression(self.parser, self.text, self.end)
            elif self.match(Token.CLOSE):
                raise ParseError('Unmatched )')
            elif self.match(Token.PIPE):
                token = Pipe(self.parser, self.text, self.end)
            elif marcel_mode and self.match(Token.REMOTE):
                token = Remote(self.parser, self.text, self.end)
            elif self.match(Token.BANG):
                token = Run(self.parser, self.text, self.end)
            elif marcel_mode and self.match(Token.ASSIGN):
                token = Assign(self.parser, self.text, self.end)
            elif marcel_mode and self.match(Token.COMMA):
                token = Comma(self.parser, self.text, self.end)
            elif marcel_mode and self.match(Token.COLON):
                token = Colon(self.parser, self.text, self.end)
            elif self.match(Token.COMMENT):
                return None  # Ignore the rest of the line
            elif self.match(Token.REDIRECT_VAR_APPEND):
                token = Arrow(self.parser, self.text, self.end, Token.REDIRECT_VAR_APPEND)
            elif self.match(Token.REDIRECT_VAR):
                token = Arrow(self.parser, self.text, self.end, Token.REDIRECT_VAR)
            elif self.match(Token.REDIRECT_FILE_APPEND):
                token = Arrow(self.parser, self.text, self.end, Token.REDIRECT_FILE_APPEND)
            elif self.match(Token.REDIRECT_FILE):
                token = Arrow(self.parser, self.text, self.end, Token.REDIRECT_FILE)
            else:
                token = (ShellString(self.parser, self.text, self.end) if self.parser.shell_op else
                         MarcelString(self.parser, self.text, self.end))
            self.end = token.end
            if self.more() and self.skip_whitespace() == 0:
                token.mark_adjacent_to_next()
        return token

    def match(self, symbol):
        return self.peek(len(symbol)) == symbol

    def skip_whitespace(self):
        before = self.end
        c = self.peek()
        while c is not None and c.isspace():
            self.next_char()
            c = self.peek()
        after = self.end
        return after - before


# ----------------------------------------------------------------------------------------------------------------------

class Tokens(object):

    def __init__(self, parser, text):
        self.lexer = Lexer(parser, text)

    def __repr__(self):
        return str(self.lexer)

    def next_token(self):
        return self.lexer.next_token()

    def mark(self):
        return self.lexer.mark()

    def reset(self, mark):
        self.lexer.reset(mark)

    # Return the next n tokens, but don't consume them. Return None if there aren't n tokens left.
    def peek(self, n=1):
        tokens = []
        mark = self.mark()
        for i in range(n):
            token = self.next_token()
            if token is None:
                tokens = None
                break
            tokens.append(token)
        self.reset(mark)
        return tokens

    def more(self):
        return self.peek() is not None


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
#             var store [op_sequence [store var]]
#             op_sequence [store var]
#             store var
#
#     op_sequence:
#             op_args | op_sequence
#             op_args
#
#     store:
#             >
#             >$
#             >>
#             >>$
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

    class ShellOpContext(object):

        def __init__(self, parser, op_token):
            self.parser = parser
            self.op_token = op_token
            self.original_shell_op = None

        def __enter__(self):
            self.original_shell_op = self.parser.shell_op
            self.parser.shell_op = self.shell_args()

        def __exit__(self, ex_type, ex_value, ex_traceback):
            self.parser.shell_op = self.original_shell_op

        def shell_args(self):
            op_name = self.op_token.value()
            var = self.parser.env.getvar(op_name) is not None
            builtin = self.op_token.is_op()
            executable = marcel.util.is_executable(op_name)
            op_module = self.parser.op_modules.get(op_name)
            bashy_args = op_module and op_module.bashy_args()
            return bashy_args or (not var and not builtin and executable)

    def __init__(self, text, main):
        self.text = text
        self.env = main.env
        self.op_modules = main.op_modules
        self.tokens = Tokens(self, text)
        self.token = None  # The current token
        self.tab_completion_context = TabCompletionContext()
        self.shell_op = False

    def __repr__(self):
        return str(self.tokens)

    def parse(self):
        if not self.tokens.more():
            raise EmptyCommand()
        return self.command()

    def command(self):
        if self.next_token(String, Assign):
            self.tab_completion_context.complete_disabled()
            command = self.assignment(self.token.value())
        else:
            self.tab_completion_context.complete_op()
            command = self.pipeline(None)
        if not self.at_end():
            raise ParseError(f'{command} followed by excess tokens')
        return command

    def assignment(self, var):
        self.next_token(Assign)
        arg = self.arg()
        if isinstance(arg, Token):
            value = arg.value()
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
        if self.next_token(String, Arrow):
            if self.token.op_name:
                op_token = self.token
                self.tab_completion_context.complete_disabled()
                found_arrow = self.next_token(Arrow)
                assert found_arrow
                arrow_token = self.token
                if self.pipeline_end():
                    # op >
                    if arrow_token.is_var():
                        raise SyntaxError(self.token, f'A variable must precede {arrow_token.value()}, '
                                                      f'not an operator ({self.token.op_name})')
                    elif arrow_token.is_file():
                        raise SyntaxError(self.token, f'A filename must precede {arrow_token.value()}, '
                                                      f'not an operator ({self.token.op_name})')
                elif self.pipeline_end(1):
                    if self.next_token(String):
                        # op > x
                        op = (op_token, [])
                        store_op = self.redirect_in_op(arrow_token, self.token)
                        op_sequence = [op, store_op]
                    else:
                        raise SyntaxError(arrow_token, f'Incorrect use of {arrow_token.value()}')
                else:
                    raise SyntaxError(arrow_token, f'Incorrect use of {arrow_token.value()}')
            else:
                self.tab_completion_context.complete_disabled()
                source = self.token
                found_arrow = self.next_token(Arrow)
                assert found_arrow
                self.tab_completion_context.complete_disabled()
                arrow_token = self.token
                load_op = self.redirect_out_op(arrow_token, source)
                if self.pipeline_end():
                    # x >
                    if arrow_token.is_append():
                        raise SyntaxError(arrow_token, 'Append not permitted here.')
                    op_sequence = [load_op]
                elif self.pipeline_end(1):
                    if self.next_token(String):
                        if self.token.op_name:
                            # x > op
                            if arrow_token.is_append():
                                raise SyntaxError(arrow_token, 'Append not permitted here.')
                            op = (self.token, [])
                            op_sequence = [load_op, op]
                        else:
                            # x > y
                            store_op = self.redirect_in_op(arrow_token, self.token)
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
                        # x > op_sequence > y
                        arrow_token = self.token
                        found_string = self.next_token(String)
                        assert found_string
                        store_op = self.redirect_in_op(arrow_token, self.token)
                        op_sequence.append(store_op)
                    else:
                        # x > op_sequence
                        if arrow_token.is_append():
                            raise SyntaxError(arrow_token, 'Append not permitted here.')
        elif self.next_token(Arrow, String):
            self.tab_completion_context.complete_disabled()
            # > x
            arrow_token = self.token
            found_string = self.next_token(String)
            assert found_string
            store_op = self.redirect_in_op(arrow_token, self.token)
            op_sequence = [store_op]
        else:
            op_sequence = self.op_sequence()
            if self.next_token(Arrow, String):
                # op_sequence > x
                arrow_token = self.token
                found_string = self.next_token(String)
                assert found_string
                store_op = self.redirect_in_op(arrow_token, self.token)
                op_sequence.append(store_op)
            # else:  op_sequence is OK as is
        for op_args in op_sequence:
            # op_args is (op_token, list of arg tokens)
            pipeline.append(self.create_op(*op_args))
        return pipeline

    def redirect_out_op(self, arrow_token, source=None):
        op_name = 'load' if arrow_token.is_var() else 'read'
        return ConstructedString(self, op_name), [] if source is None else [source]

    def redirect_in_op(self, arrow_token, target):
        op_name = 'store' if arrow_token.is_var() else 'write'
        return ConstructedString(self, op_name), ['--append', target] if arrow_token.is_append() else [target]

    def map_op(self, expr):
        return ConstructedString(self, 'map'), [expr]

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
            op_args = (ConstructedString(self, 'map'), [self.token])
        else:
            op_token = self.op()
            # ShellOpContext sets the parser to expect shell arg tokens (ShellString) or
            # marcel arg tokens MarcelString.
            with Parser.ShellOpContext(self, op_token):
                arg_tokens = []
                if not op_token.adjacent_to_next:
                    # Token is followed by whitespace
                    self.tab_completion_context.complete_arg(op_token)
                arg_token = self.arg()
                while arg_token is not None:
                    arg_tokens.append(arg_token)
                    arg_token = self.arg()
                op_args = (op_token, arg_tokens)
        return op_args

    def op(self):
        if self.next_token(String) or self.next_token(Remote) or self.next_token(Run):
            return self.token
        else:
            raise PrematureEndError(self.token)

    def arg(self):
        def marcel_arg():
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
            elif self.next_token(String) or self.next_token(Expression):
                return self.token
            else:
                return None

        def shell_arg():
            if self.next_token(Expression) or self.next_token(ShellString):
                return self.token
            else:
                return None
        return shell_arg() if self.shell_op else marcel_arg()

    def vars(self):
        vars = []
        while self.token.is_string():
            vars.append(self.token.value())
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

    # Looks for a sequence of tokens matching the types listed in expected_token_types.
    # Returns True if a sequence of qualifying token was found, and advances to the first of those.
    # Returns False if a sequence of qualifying token was not found, and leaves the current token unchanged.
    def next_token(self, *expected_token_types):
        n = len(expected_token_types)
        if n > 0:
            tokens = self.tokens.peek(n)
            if tokens is None:
                return False
            for i in range(n):
                if not isinstance(tokens[i], expected_token_types[i]):
                    return False
        self.token = self.tokens.next_token()
        return True

    # Does token t+n indicate the end of a pipeline?
    def pipeline_end(self, n=0):
        tokens = self.tokens.peek(n + 1)
        return tokens is None or tokens[-1].is_end()

    def at_end(self):
        return self.tokens.peek() is None

    @staticmethod
    def raise_unexpected_token_error(token, message):
        raise SyntaxError(token, message)

    def create_op(self, op_token, arg_tokens):
        op = self.create_op_variable(op_token, arg_tokens)
        if op is None:
            op = self.create_op_builtin(op_token, arg_tokens)
        if op is None:
            op = self.create_op_executable(op_token, arg_tokens)
        if op is None:
            raise marcel.exception.KillCommandException(f'{op_token.value()} is not defined.')
        return op

    def create_op_builtin(self, op_token, arg_tokens):
        op = None
        if op_token.is_op():
            op_name = op_token.op_name
            op_module = self.op_modules[op_name]
            op = op_module.create_op()
            # Both ! and !! map to the run op.
            if op_name == 'run':
                # !: Expect a command number
                # !!: Don't expect a command number, run the previous command
                # else: 'run' was entered
                op.expected_args = (1 if op_token.value() == '!' else
                                    0 if op_token.value() == '!!' else None)
            args = []
            if op_name == 'bash':
                for x in arg_tokens:
                    args.append(x.raw() if isinstance(x, String) else
                                x.value() if isinstance(x, Token) else
                                x)
            else:
                for x in arg_tokens:
                    args.append(x.value() if isinstance(x, Token) else x)
                self.tab_completion_context.set_op(op, op_module.args_parser().flags())
            op_module.args_parser().parse(args, op)
        return op

    def create_op_variable(self, op_token, arg_tokens):
        var = op_token.value()
        if self.env.getvar(var) is None:
            return None
        op = self.op_modules['runpipeline'].create_op()
        op.var = var
        if len(arg_tokens) > 0:
            pipeline_args = []
            for token in arg_tokens:
                pipeline_args.append(token
                                     if type(token) is marcel.core.Pipeline else
                                     token.value())
            args, kwargs = marcel.argsparser.PipelineArgsParser(var).parse_pipeline_args(pipeline_args)
            op.set_pipeline_args(args, kwargs)
        return op

    def create_op_executable(self, op_token, arg_tokens):
        op = None
        name = op_token.value()
        if marcel.util.is_executable(name):
            args = [name]
            for x in arg_tokens:
                args.append(x.raw() if isinstance(x, String) else
                            x.value() if isinstance(x, Token) else
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
