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

import io
import tokenize as tkn
from enum import Enum


class State(Enum):
    START = 1
    ARGLIST = 2
    STAR = 3
    ARG = 4
    END = 5
    NO_ARGS = 6

    def terminal(self):
        return self in (State.END, State.NO_ARGS)


class Symbol(Enum):
    LAMBDA = 1,
    NAME = 2,
    COMMA = 3,
    STAR = 4,
    COLON = 5,
    OTHER = 6

    @staticmethod
    def of(token):
        return (Symbol.LAMBDA if token.type == tkn.NAME and token.string == 'lambda' else
                Symbol.NAME if token.type == tkn.NAME else
                Symbol.COMMA if token.type == tkn.OP and token.string == ',' else
                Symbol.STAR if token.type == tkn.OP and token.string == '*' else
                Symbol.COLON if token.type == tkn.OP and token.string == ':' else
                Symbol.OTHER)


# For parsing the beginning of an Expression, looking for the arguments of a function.
# There may not be any, as in (5+6) or (lambda: 5+6). Marcel syntax is supported, so
# "lambda" may be omitted. Tracks presence of lambda, and whether args are present at all.
class FunctionArgsParser(object):

    def __init__(self, source):
        self.state = State.START
        self.explicit_lambda = False
        self.explicit_colon = False
        self.has_args = False
        self.input = io.BytesIO(source.encode('utf-8')).readline
        self.transitions = {
            (State.START, Symbol.LAMBDA): self.start_lambda,
            (State.START, Symbol.STAR): self.start_star,
            (State.START, Symbol.NAME): self.start_name,
            (State.START, Symbol.COLON): self.start_colon,
            (State.ARGLIST, Symbol.NAME): self.arglist_name,
            (State.ARGLIST, Symbol.STAR): self.arglist_star,
            (State.ARGLIST, Symbol.COLON): self.arglist_colon,
            (State.STAR, Symbol.NAME): self.star_name,
            (State.ARG, Symbol.COMMA): self.arg_comma,
            (State.ARG, Symbol.COLON): self.arg_colon
        }

    def __repr__(self):
        return (f'({str(self.state)}, '
                f'lambda: {self.explicit_lambda}, '
                f'colon: {self.explicit_colon}, '
                f'args: {self.has_args})')

    def parse(self):
        def transition(symbol):
            handler = self.transitions.get((self.state, symbol), None)
            return handler() if handler else State.NO_ARGS

        for token in tkn.tokenize(self.input):
            if token.type == tkn.ENDMARKER:
                break
            if token.type not in (tkn.ENCODING, tkn.NEWLINE):
                self.state = transition(Symbol.of(token))
                if self.state.terminal():
                    break
        if self.state != State.END:
            self.explicit_lambda = False
            self.explicit_colon = False
            self.has_args = False

    def start_lambda(self):
        self.explicit_lambda = True
        return State.ARGLIST

    def start_star(self):
        return State.STAR

    def start_name(self):
        self.has_args = True
        return State.ARG

    def start_colon(self):
        self.explicit_colon = True
        return State.END

    def arglist_name(self):
        self.has_args = True
        return State.ARG

    def arglist_star(self):
        return State.STAR

    def arglist_colon(self):
        self.explicit_colon = True
        return State.END

    def star_name(self):
        return State.ARG

    def arg_comma(self):
        return State.ARGLIST

    def arg_colon(self):
        self.explicit_colon = True
        return State.END
