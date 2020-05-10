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
                f'Malformed Python expression {self.text[self.start:self.end]}')


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
                        f'Malformed string: {self.text[self.start:self.end]}')
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
    DONE = auto()
    END = auto()
    OP = auto()
    ARGS = auto()


class UnexpectedTokenError(Exception):

    def __init__(self, text, position, message):
        self.text = text
        self.position = position
        self.message = message

    def __str__(self):
        return f'Parsing error at position {self.position} of "{self.text}": {self.message}'


class PrematureEndError(UnexpectedTokenError):

    def __init__(self, text):
        super().__init__(text, None, None)

    def __str__(self):
        return f'Command ended prematurely: {self.text}'


class UnknownOpError(UnexpectedTokenError):

    def __init__(self, text, op_name):
        super().__init__(text, None, None)
        self.op_name = op_name

    def __str__(self):
        return f'Unknown command: {self.op_name}'


class InProgress:

    def __init__(self):
        self.pipeline = marcel.core.Pipeline()
        self.op_name = None
        self.args = []

    def reset_op(self):
        self.op_name = None
        self.args.clear()


class Parser(Token):

    def __init__(self, text, op_modules):
        super().__init__(text, 0)
        self.op_modules = op_modules
        self.state = ParseState.START
        self.stack = marcel.util.Stack()
        self.stack.push(InProgress())
        self.op_name = None  # For use by tabcompleter

    def __repr__(self):
        return f'parser({self.text})'

    def set_op_name(self, op_name):
        self.current().op_name = op_name
        self.op_name = op_name if self.is_op() else None

    def current(self):
        return self.stack.top()

    def start_action(self, token):
        if token.is_fork():
            self.set_op_name('fork')
            self.state = ParseState.OP
        elif token.is_string() or token.is_fork():
            self.set_op_name(token.value())
            self.state = ParseState.OP
        elif token is None:
            raise PrematureEndError(self.text)
        else:
            raise UnexpectedTokenError(self.text, self.end, 'Expected string')

    def end_action(self, token):
        if token is None:
            self.finish_command()
            self.state = ParseState.DONE
        elif token.is_pipe():
            self.finish_op()
            self.state = ParseState.START
        elif token.is_string() or token.is_expr():
            self.current().args.append(token.value())
            self.state = ParseState.ARGS
        else:
            raise UnexpectedTokenError(self.text, self.end, 'Expected pipe or end of input')

    def op_action(self, token):
        if token is None:
            self.finish_op()
            self.state = ParseState.DONE
        elif token.is_string() or token.is_expr():
            arg = token.value()
            self.current().args.append(arg)
            self.state = ParseState.ARGS
        elif token.is_pipe():
            self.finish_op()
            self.state = ParseState.START
        elif token.is_begin():
            self.stack.push(InProgress())
            self.state = ParseState.START
        elif token.is_end():
            self.finish_op()
            self.finish_pipeline()
            self.state = ParseState.END
        else:
            raise UnexpectedTokenError(self.text, self.end, 'Expected string or pipe')

    def args_action(self, token):
        if token is None:
            self.finish_op()
            self.state = ParseState.DONE
        elif token.is_string() or token.is_expr():
            arg = token.value()
            self.current().args.append(arg)
        elif token.is_pipe():
            self.finish_op()
            self.state = ParseState.START
        elif token.is_begin():
            self.stack.push(InProgress())
            self.state = ParseState.START
        elif token.is_end():
            self.finish_op()
            self.finish_pipeline()
            self.state = ParseState.END
        else:
            raise UnexpectedTokenError(self.text, self.end, 'Expected string or pipe')

    # partial_text is True for parsing done during tab completion
    def parse(self, partial_text=False):
        try:
            token = self.next_token()
            while self.state != ParseState.DONE:
                if self.state == ParseState.OP:
                    self.op_action(token)
                elif self.state == ParseState.ARGS:
                    self.args_action(token)
                elif self.state == ParseState.START:
                    self.start_action(token)
                elif self.state == ParseState.END:
                    self.end_action(token)
                else:
                    assert False
                token = self.next_token()
            pipeline = self.stack.pop().pipeline
            assert self.stack.is_empty()
            return pipeline
        except UnknownOpError as e:
            # An unknown op could occur because someone got an op wrong. I.e., we are parsing complete text
            # (partial_text is False) and the op is just wrong. But it could also occur if we are doing tab
            # completion (partial_text is True), and we have an op prefix, which is the whole point of
            # tab completion. In the latter case, the UnknownOpError is not exceptional.
            if not partial_text:
                raise marcel.exception.KillCommandException(e)
        except Exception as e:
            raise marcel.exception.KillCommandException(e)

    def next_token(self):
        token = None
        self.skip_whitespace()
        c = self.peek_char()
        if c is not None:
            if c == Token.OPEN:
                token = PythonExpression(self.text, self.end)
            elif c == Token.CLOSE:
                raise UnexpectedTokenError(self.text, self.end, 'Unmatched )')
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

    def skip_whitespace(self):
        c = self.peek_char()
        while c is not None and c.isspace():
            self.next_char()
            c = self.peek_char()

    def is_op(self):
        op_name = self.current().op_name
        return self.op_modules.get(op_name, None) is not None or marcel.util.is_executable(op_name)

    def finish_op(self):
        # Get the op module, bash in case of an executable.
        current = self.current()
        op_name = current.op_name
        try:
            op_module = self.op_modules[op_name]
        except KeyError:
            if marcel.util.is_executable(op_name):
                op_module = self.op_modules['bash']
                current.args = [op_name] + current.args
            else:
                raise UnknownOpError(self.text, op_name)
        # Create the op
        op = op_module.create_op()
        # Parse its args
        arg_parser = op_module.arg_parser()
        current = self.current()
        arg_parser.parse_args(current.args, namespace=op)
        # Append the op to the pipeline
        current.pipeline.append(op)
        # Clear op state
        current.reset_op()

    def finish_pipeline(self):
        fork_pipeline = self.stack.pop().pipeline
        current = self.current()
        current.args.append(fork_pipeline)

    def finish_command(self):
        self.finish_op()
