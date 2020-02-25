from enum import Enum, auto

import marcel.core
import marcel.core
import marcel.exception
import marcel.exception
import marcel.op.fork
import marcel.opmodules
from marcel.util import *


class MalformedStringError(Exception):

    def __init__(self, text, message):
        super().__init__(message)
        self.text = text


class Token:
    # Special characters that need to be escaped for python strings
    ESCAPABLE = '''\\\'\"\a\b\f\n\r\t\v'''
    SINGLE_QUOTE = "'"
    DOUBLE_QUOTE = '"'
    QUOTES = SINGLE_QUOTE + DOUBLE_QUOTE
    ESCAPE_CHAR = '\\'
    OPEN = '('
    CLOSE = ')'
    PIPE = '|'
    FORK = '@'
    BEGIN = '['
    END = ']'
    STRING_TERMINATING = [OPEN, CLOSE, PIPE, BEGIN, END]

    def __init__(self, text, position):
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

    def is_string(self):
        return False

    def is_fork(self):
        return False

    def is_pipe(self):
        return False

    def is_expr(self):
        return False

    def is_begin(self):
        return False

    def is_end(self):
        return False

    def value(self):
        return None


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


class PythonExpression(Token):

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
                'Malformed Python expression {}'.format(self.text[self.start:self.end]))


class ShellString(Token):

    def __init__(self, text, position):
        super().__init__(text, position)
        self.string = None
        self.scan()

    def is_string(self):
        return True

    def value(self):
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
                        'Malformed string: {}'.format(self.text[self.start:self.end]))
            else:
                chars.append(c)
        self.string = ''.join(chars)


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


class ParseState(Enum):
    START = auto()
    END = auto()
    FORK_START = auto()
    FORK_SPEC = auto()
    FORK_END = auto()
    OP = auto()
    ESCAPE = auto()
    ARGS = auto()


class UnexpectedTokenError(Exception):

    def __init__(self, text, position, message):
        self.text = text
        self.position = position
        self.message = message

    def __repr__(self):
        return 'Parsing error at {}: {}'.format(self.text[self.position:self.position + 20], self.message)


class Parser(Token):

    def __init__(self, text):
        super().__init__(text, 0)
        self.state = ParseState.START
        self.pipelines = Stack()
        self.pipelines.push(marcel.core.Pipeline())
        self.fork_spec = None
        self.op = None
        self.args = []

    def start_action(self, token):
        if token.is_fork():
            self.state = ParseState.FORK_START
        elif token.is_string():
            op_name = token.value()
            op_module = marcel.opmodules.OP_MODULES.named(op_name)
            self.op = getattr(op_module, op_name)()
            self.state = ParseState.OP
        else:
            raise UnexpectedTokenError(self.text, self.end, 'Expected string')

    def end_action(self, token):
        assert token is None

    def fork_start_action(self, token):
        if token.is_string():
            x = token.value()
            self.fork_spec = int(x) if x.isdigit() else x
            self.state = ParseState.FORK_SPEC
        else:
            raise UnexpectedTokenError(self.text, self.end, 'Expected fork specification')

    def fork_end_action(self, token):
        if token is None:
            self.state = ParseState.END
        elif token.is_pipe():
            self.state = ParseState.START
        else:
            raise UnexpectedTokenError(self.text, self.end, 'Expected pipe or end of input')

    def fork_spec_action(self, token):
        if token.is_begin():
            fork_pipeline = marcel.core.Pipeline()
            self.pipelines.push(fork_pipeline)
            self.op = fork_pipeline
            self.state = ParseState.START
        else:
            raise UnexpectedTokenError(self.text, self.end, 'Expected pipeline begin')

    def op_action(self, token):
        if token is None:
            self.finish_op()
            self.state = ParseState.END
        elif token.is_string():
            self.args.append(token.value())
            self.state = ParseState.ARGS
        elif token.is_expr():
            self.args.append(token.value())
            self.state = ParseState.ARGS
        elif token.is_pipe():
            self.finish_op()
            self.state = ParseState.START
        elif token.is_end():
            self.finish_op()
            self.finish_pipeline()
            self.state = ParseState.FORK_END
        else:
            raise UnexpectedTokenError(self.text, self.end, 'Expected string or pipe')

    def escape_action(self, token):
        if token.is_string():
            self.args.append(token.value())
            self.state = ParseState.ARGS
        else:
            raise UnexpectedTokenError(self.text, self.end, 'Expected escape command')

    def args_action(self, token):
        if token is None:
            self.finish_op()
            self.state = ParseState.END
        elif token.is_string():
            self.args.append(token.value())
        elif token.is_expr():
            self.args.append(token.value())
        elif token.is_pipe():
            self.finish_op()
            self.state = ParseState.START
        elif token.is_end():
            self.finish_op()
            self.finish_pipeline()
            self.state = ParseState.FORK_END
        else:
            raise UnexpectedTokenError(self.text, self.end, 'Expected string or pipe')

    def parse(self):
        try:
            token = self.next_token()
            while self.state != ParseState.END:
                if self.state == ParseState.START:
                    self.start_action(token)
                elif self.state == ParseState.FORK_START:
                    self.fork_start_action(token)
                elif self.state == ParseState.FORK_END:
                    self.fork_end_action(token)
                elif self.state == ParseState.FORK_SPEC:
                    self.fork_spec_action(token)
                elif self.state == ParseState.OP:
                    self.op_action(token)
                elif self.state == ParseState.ESCAPE:
                    self.escape_action(token)
                elif self.state == ParseState.ARGS:
                    self.args_action(token)
                else:
                    assert False
                token = self.next_token()
            self.end_action(token)
            pipeline = self.pipelines.pop()
            assert self.pipelines.is_empty()
            return pipeline
        except Exception as e:
            raise marcel.exception.KillCommandException(e)

    def next_token(self):
        token = None
        self.skip_whitespace()
        c = self.peek_char()
        if c is not None:
            if c == Token.OPEN:
                token = PythonExpression(self.text, self.end)
            elif c == Token.PIPE:
                token = Pipe(self.text, self.end)
            elif c == Token.BEGIN:
                token = Begin(self.text, self.end)
            elif c == Token.END:
                token = End(self.text, self.end)
            elif c == Token.FORK:
                token = Fork(self.text, self.end)
            else:
                token = ShellString(self.text, self.end)
            self.end = token.end
        return token

    def finish_op(self):
        self.op.arg_parser().parse_args(self.args, namespace=self.op)
        self.pipeline().append(self.op)
        self.op = None
        self.args = []

    def finish_pipeline(self):
        fork_pipeline = self.pipelines.pop()
        main_pipeline = self.pipelines.top()
        main_pipeline.append(marcel.op.fork.Fork(self.fork_spec, fork_pipeline))
        self.fork_spec = None

    def pipeline(self):
        return self.pipelines.top()

    def skip_whitespace(self):
        c = self.peek_char()
        while c is not None and c.isspace():
            self.next_char()
            c = self.peek_char()
