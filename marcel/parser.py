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

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.function
import marcel.opmodule
import marcel.util
from marcel.function_args_parser import FunctionArgsParser
from marcel.stringliteral import StringLiteral


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

class Source(object):

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
    WRITE_FILE = '>'
    WRITE_FILE_APPEND = '>>'
    WRITE_VAR = '>$'
    WRITE_VAR_APPEND = '>>$'
    READ_FILE = '<'
    READ_VAR = '<$'
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
        READ_FILE,
        READ_VAR,
        WRITE_FILE,
        WRITE_FILE_APPEND,
        WRITE_VAR,
        WRITE_VAR_APPEND
    ]
    SHELL_STRING_TERMINATING = [
        OPEN,
        CLOSE,
        PIPE,
        READ_FILE,
        READ_VAR,
        WRITE_FILE,
        WRITE_FILE_APPEND,
        WRITE_VAR,
        WRITE_VAR_APPEND
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

    def is_var(self):
        return False

    def is_executable(self):
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

    def is_gt(self):
        return False

    def is_lt(self):
        return False

    def is_lexer_failure(self):
        return False

    def op_name(self):
        return None

    def missing_quote(self):
        return None

    def mark_adjacent_to_next(self):
        self.adjacent_to_next = True

    # The lexical end of this token matches the end of the command being parsed. I.e., no whitespace
    # (or anything else) after the token.
    def is_terminal(self):
        assert self.end is not None
        return self.end == len(self.parser.text)


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
        self._for_assignment = False
        self.scan()

    # The result of evaluation this expression is a function.
    def value(self):
        try:
            if self._function is None:
                globals = self.parser.env.namespace
                # source may be used for compilation eventually, so it has to be valid Python source which, when
                # evaluated yields a function. (I.e., not the source of marcel shorthand, omitting lambda.)
                source = self.source()
                function_args_parser = FunctionArgsParser(source)
                function_args_parser.parse()
                # Source may need to be tweaked. E.g. for "inc = (lambda f: f + 1)", we want to return the function,
                # not the evaluation of the function, so prepend "lambda: ".
                # The rationale and details are discussed in notes/function_notation.txt
                if function_args_parser.explicit_lambda:
                    if function_args_parser.has_args and self._for_assignment:
                        prefix = 'lambda: '
                    else:
                        prefix = ''
                else:
                    if function_args_parser.has_args:
                        prefix = 'lambda: lambda ' if self._for_assignment else 'lambda '
                    else:
                        prefix = 'lambda ' if function_args_parser.explicit_colon else 'lambda: '
                source = prefix + source
                function = eval(source, globals)
                self._function = marcel.function.SourceFunction(function=function, source=source)
            return self._function
        except Exception as e:
            raise marcel.exception.KillCommandException(f'Error in function "{self.source()}": {e}')

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

    def mark_for_assignment(self):
        self._for_assignment = True


class String(Token):

    def __init__(self, parser, text, position, scan_termination):
        assert position >= 0
        super().__init__(parser, text, position)
        self.string = None
        self.scan(scan_termination)
        # op_modules is a dict, name -> OpModule
        op_module = parser.op_modules.get(self.string, None)
        self.op_name = self.string if op_module and op_module.public_op() else None

    def value(self):
        return self.string

    def is_string(self):
        return True

    def is_op(self):
        return self.op_name is not None

    def is_var(self):
        return self.parser.env.getvar(self.string) is not None

    def is_executable(self):
        return marcel.util.is_executable(self.string)

    def missing_quote(self):
        return self.string.missing_quote()

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
                chars.append(c)
                if quote is None:
                    quote = c
                elif c == quote:
                    quote = None
            elif c == Token.ESCAPE_CHAR:
                if quote is None:
                    # TODO: ESCAPE at end of line
                    chars.append(c)
                    c = self.next_char()
                    if c is None:
                        break
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
        self.string = StringLiteral(''.join(chars))


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


class Gt(Symbol):

    def __init__(self, parser, text, position, symbol):
        super().__init__(parser, text, position, symbol)
        assert symbol in (Token.WRITE_VAR, Token.WRITE_VAR_APPEND,
                          Token.WRITE_FILE, Token.WRITE_FILE_APPEND)

    def is_gt(self):
        return True

    def is_var(self):
        return self.symbol in (Token.WRITE_VAR, Token.WRITE_VAR_APPEND)

    def is_file(self):
        return self.symbol in (Token.WRITE_FILE, Token.WRITE_FILE_APPEND)

    def is_append(self):
        return self.symbol in (Token.WRITE_VAR_APPEND, Token.WRITE_FILE_APPEND)
    
    
class Lt(Symbol):

    def __init__(self, parser, text, position, symbol):
        super().__init__(parser, text, position, symbol)
        assert symbol in (Token.READ_VAR, Token.READ_FILE)

    def is_lt(self):
        return True

    def is_var(self):
        return self.symbol == Token.READ_VAR

    def is_file(self):
        return self.symbol == Token.READ_FILE


class LexerFailure(Token):

    def __init__(self, exception):
        super().__init__(parser=None, text=None, position=None)
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
        if token is None:
            consolidated = None
        else:
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
            elif self.match(Token.WRITE_VAR_APPEND):
                token = Gt(self.parser, self.text, self.end, Token.WRITE_VAR_APPEND)
            elif self.match(Token.WRITE_VAR):
                token = Gt(self.parser, self.text, self.end, Token.WRITE_VAR)
            elif self.match(Token.WRITE_FILE_APPEND):
                token = Gt(self.parser, self.text, self.end, Token.WRITE_FILE_APPEND)
            elif self.match(Token.WRITE_FILE):
                token = Gt(self.parser, self.text, self.end, Token.WRITE_FILE)
            elif self.match(Token.READ_VAR):
                token = Lt(self.parser, self.text, self.end, Token.READ_VAR)
            elif self.match(Token.READ_FILE):
                token = Lt(self.parser, self.text, self.end, Token.READ_FILE)
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
#             str = arg
#    
#     pipeline:
#             op_sequence [gt str]
#             str lt gt str
#             str lt [op_sequence [gt str]]
#             gt str
#
#     op_sequence:
#             op_args | op_sequence
#             op_args
#
#     lt:
#             <
#             <$
#     gt:
#             gt1
#             gt2
#
#     gt1:
#             >
#             >$
#
#     gt2:
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
#             vars, str
#             str
#
#     expr: Expression
#
#     str: String
#
#     begin: (|
#
#     end: |)
# 
# Pipeline parsing semantics:
#
# store means either Write or Store, depending on the arrow, e.g. > or >$).
# Similarly, read means either Read or Load.
#
# - op_sequence [arrow str]
#
#     Equivalent to: op_sequence | store str
#
# - str arrow1 arrow str:
#
#     Equivalent to: read str | write str
#
# - str arrow1 [op_sequence [arrow str]]:
#
#     Equivalent to: read str | [op_sequence [| store str]]

# Tracks op_args parsing, so that we know if we are currently parsing an op or arg.
# Useful for tab completion (only, right now).
class OpArgContext(object):
    OTHER = 'OTHER'
    OP = 'OP'
    FLAG = 'FLAG'
    ARG = 'ARG'

    def __init__(self, env):
        self.env = env
        self.context = None
        # Assume we start parsing an op. If we aren't, the parser will call reset().
        self.set_op()

    def __repr__(self):
        return self.context

    def is_op(self):
        return self.context == OpArgContext.OP

    def is_flag(self):
        return self.context == OpArgContext.FLAG

    def is_arg(self):
        return self.context == OpArgContext.ARG

    def reset(self):
        self.context = OpArgContext.OTHER

    def set_op(self):
        self.context = OpArgContext.OP

    def set_flag(self):
        self.context = OpArgContext.FLAG

    def set_arg(self):
        self.context = OpArgContext.ARG


class Parser(object):

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

    class PipelineSourceTracker(object):

        def __init__(self, parser, pipeline):
            self.parser = parser
            self.pipeline = pipeline
            self.start_position = None
            self.arg_count = 0
            self.op_token = None
            self.prev_op_arg_context = None

        def __enter__(self):
            self.parser.pipeline_stack.append(self)
            self.start_position = self._current_position()
            self.prev_op_arg_context = self.parser.op_arg_context
            self.parser.op_arg_context = OpArgContext(self.parser.env)
            return self

        def __exit__(self, ex_type, ex_value, ex_traceback):
            if self.parser.tokens.more():
                assert self.parser.current_pipeline() == self
                self.parser.pipeline_stack.pop()
                end_position = self._current_position()
                self.pipeline.source = self.parser.text[self.start_position:end_position].strip()
                self.parser.op_arg_context = self.prev_op_arg_context
            # else: Keep the stack as is, for tab completion

        def _current_position(self):
            # Lexer.mark() returns text, start, end
            return self.parser.tokens.lexer.mark()[2]

    def __init__(self, text, env):
        self.text = text
        self.env = env
        self.op_modules = env.op_modules
        self.tokens = Tokens(self, text)
        self.token = None  # The current token
        self.shell_op = False
        self.pipeline_stack = []  # Contains PipelineSourceTrackers
        self.op_arg_context = OpArgContext(env)

    def __repr__(self):
        return str(self.tokens)

    def parse(self):
        if not self.tokens.more():
            raise EmptyCommand()
        return self.command()

    def terminal_token_value(self):
        return self.token.value() if self.token.is_terminal() else ''

    # Used by Compilable which contains function source and caches the compiled function.
    def parse_function(self):
        token = self.arg()
        # assert type(token) is Expression, f'({type(token)}) {token} '
        return token.value()

    # Used by Compilable which contains pipeline source and caches the compiled pipeline.
    def parse_pipeline(self):
        pipeline = self.pipeline()
        assert type(pipeline) is marcel.core.PipelineExecutable
        return pipeline

    def command(self):
        if self.next_token(String, Assign):
            command = self.assignment(self.token.value())
        else:
            command = self.pipeline()
        if not self.at_end():
            raise ParseError(f'{command} followed by excess tokens')
        return command

    def assignment(self, var):
        self.op_arg_context.reset()
        self.next_token(Assign)
        arg = self.arg()
        source = None
        if isinstance(arg, Token):
            if isinstance(arg, Expression):
                source = arg.source()
                arg.mark_for_assignment()
            value = arg.value()
        elif type(arg) is marcel.core.PipelineExecutable:
            value = arg
            source = arg.source
        elif arg is None:
            raise SyntaxError(self.token, 'Unexpected token type.')
        else:
            assert False, arg
        op = self.create_assignment(var, value, source)
        return op
    
    def pipeline(self):
        def pipeline_str_lt():
            self.op_arg_context.reset()
            source = self.token  # var or file, depending on arrow type
            found_lt = self.next_token(Lt)
            assert found_lt
            lt = self.token
            if self.next_token(Gt):
                # str lt gt str
                gt = self.token
                if self.next_token(String):
                    target = self.token
                    op_sequence = [self.redirect_in_op(lt, source),
                                   self.redirect_out_op(gt, target)]
                else:
                    raise SyntaxError(self.token, 'Invalid redirection target')
            else:
                # str lt [op_sequence [gt str]]
                op_sequence = [self.redirect_in_op(lt, source)]
                if not self.pipeline_end():
                    op_sequence.extend(self.op_sequence())
                    if self.next_token(Gt, String):
                        gt = self.token
                        found_string = self.next_token(String)
                        assert found_string
                        target = self.token
                        op_sequence.append(self.redirect_out_op(gt, target))
            return op_sequence

        def pipeline_gt_str():
            self.op_arg_context.reset()
            gt = self.token
            if self.next_token(String):
                op_sequence = [self.redirect_out_op(gt, self.token)]
            else:
                raise SyntaxError(self.token, 'Invalid redirection target')
            return op_sequence

        def pipeline_op_sequence():
            op_sequence = self.op_sequence()
            if self.next_token(Gt, String):
                # op_sequence > f
                arrow_token = self.token
                found_string = self.next_token(String)
                assert found_string
                store_op = self.redirect_out_op(arrow_token, self.token)
                op_sequence.append(store_op)
            # else:  op_sequence is OK as is
            return op_sequence

        pipeline = marcel.core.PipelineExecutable()
        with Parser.PipelineSourceTracker(self, pipeline):
            # If the next tokens are var comma, or var colon, then we have
            # pipeline variables being declared.
            if self.next_token(String, Comma) or self.next_token(String, Colon):
                parameters = self.vars()
            else:
                parameters = None
            pipeline.set_parameters(parameters)
            op_sequence = (pipeline_str_lt() if self.next_token(String, Lt) else
                           pipeline_gt_str() if self.next_token(Gt, String) else
                           pipeline_op_sequence())
            for op_args in op_sequence:
                pipeline.append(self.create_op(*op_args))
        return pipeline

    def redirect_in_op(self, arrow_token, source=None):
        op_name = 'load' if arrow_token.is_var() else 'read'
        return ConstructedString(self, op_name), [] if source is None else [source]

    def redirect_out_op(self, arrow_token, target):
        op_name = 'store' if arrow_token.is_var() else 'write'
        return ConstructedString(self, op_name), ['--append', target] if arrow_token.is_append() else [target]

    def map_op(self, expr):
        return ConstructedString(self, 'map'), [expr]

    def op_sequence(self):
        op_args = [self.op_args()]
        if self.next_token(Pipe):
            return op_args + self.op_sequence()
        else:
            return op_args

    # Returns (op name, list of arg tokens)
    def op_args(self):
        self.start_counting_args()
        if self.next_token(Expression):
            op_token = ConstructedString(self, 'map')
            arg_tokens = [self.token]
        else:
            op_token = self.op()
            arg_tokens = []
            # ShellOpContext sets the parser to expect shell arg tokens (ShellString) or
            # marcel arg tokens MarcelString.
            with Parser.ShellOpContext(self, op_token):
                arg_token = self.arg()
                while arg_token is not None:
                    arg_tokens.append(arg_token)
                    arg_token = self.arg()
        self.current_pipeline().op_token = op_token
        return op_token, arg_tokens

    def op(self):
        self.op_arg_context.set_op()
        if self.next_token(String) or self.next_token(Remote) or self.next_token(Run):
            return self.token
        else:
            raise PrematureEndError(self.token)

    def arg(self):
        def marcel_arg():
            if self.next_token(Begin):
                pipeline = self.pipeline()
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

        def set_op_arg_context():
            next_token = self.tokens.peek()  # None or a list
            if next_token is not None:
                next_token = next_token[0]
            if next_token is None:
                if self.text[-1].isspace():
                    self.op_arg_context.set_arg()
                # else: No space after op. We're still in an op context
            elif isinstance(next_token, String):
                if next_token.value().startswith('-'):
                    self.op_arg_context.set_flag()
                else:
                    self.op_arg_context.set_arg()
            else:
                self.op_arg_context.reset()

        self.count_arg()
        set_op_arg_context()
        arg = shell_arg() if self.shell_op else marcel_arg()
        if isinstance(arg, String) and arg.missing_quote():
            raise marcel.exception.MissingQuoteException(arg.value())
        return arg

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
            # op is not a variable, operator, or executable. Assume that it's an undefined variable,
            # whose value will make sense at execution time, (e.g. xyz in p = (| xyz ... |)). In other
            # contexts, the undefined variable will need to be detected during command execution, e.g.
            # executing xyz ...
            op = self.create_op_variable(op_token, arg_tokens, undefined_var_ok=True)
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
            for x in arg_tokens:
                args.append(x.value() if isinstance(x, Token) else x)
            op_module.args_parser(self.env).parse(args, op)
        return op

    def create_op_variable(self, op_token, arg_tokens, undefined_var_ok=False):
        if op_token.is_var() or undefined_var_ok:
            var = op_token.value()
            op = self.op_modules['runpipeline'].create_op()
            op.var = var
            if len(arg_tokens) > 0:
                pipeline_args = []
                for token in arg_tokens:
                    pipeline_args.append(token
                                         if type(token) is marcel.core.PipelineExecutable else
                                         token.value())
                args, kwargs = marcel.argsparser.PipelineArgsParser(var).parse_pipeline_args(pipeline_args)
                op.set_pipeline_args(args, kwargs)
            return op
        else:
            return None

    def create_op_executable(self, op_token, arg_tokens):
        op = None
        if op_token.is_executable():
            name = op_token.value()
            args = [name]
            for x in arg_tokens:
                args.append(x.raw() if isinstance(x, String) else
                            x.value() if isinstance(x, Token) else
                            x)
            op = marcel.opmodule.create_op(self.env, 'bash', *args)
        return op

    def create_assignment(self, var, value, source):
        assign_module = self.op_modules['assign']
        assert assign_module is not None
        op = assign_module.create_op()
        op.set_var_and_value(var, value, source)
        pipeline = marcel.core.PipelineExecutable()
        pipeline.append(op)
        return pipeline

    # Tab completion support

    def current_pipeline(self):
        return self.pipeline_stack[-1] if len(self.pipeline_stack) > 0 else None

    def start_counting_args(self):
        self.current_pipeline().arg_count = -1

    def count_arg(self):
        pipeline = self.current_pipeline()
        if pipeline:
            pipeline.arg_count += 1

    def expect_op(self):
        pipeline = self.current_pipeline()
        if pipeline:
            if pipeline.arg_count == 0:
                return (self.token.is_string() and
                        self.token.value().isidentifier() and
                        not self.text[-1].isspace())
            elif pipeline.arg_count < 0:
                return True
        return False

    def flags(self):
        flags = []
        pipeline = self.current_pipeline()
        if pipeline and pipeline.op_token:
            flag_args = self.op_modules[pipeline.op_token.value()].args_parser(self.env).flag_args
            for flag in flag_args:
                if flag.short:
                    flags.append(flag.short)
                if flag.long:
                    flags.append(flag.long)
        return flags
