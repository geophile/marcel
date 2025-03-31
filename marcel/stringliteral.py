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

# Subclass of str that includes metacharacters from the string's creation as a literal: quotes, escape.
class StringLiteral(str):

    QUOTES = '"\''

    def __new__(cls, literal=None):
        return super().__new__(cls, literal)

    def __init__(self, literal=None):
        self.original = literal
        self.escape = None
        self.quote = None
        self.unterminated_quote = None
        self.string = None
        self.compute_unadorned()

    def value(self):
        return self.string

    def description(self):
        return (f'{self.original} -> {self.string}, '
                f'escaped={self.escape}, '
                f'quote={self.quote}, '
                f'missing_quote={self.missing_quote}')

    def escaped(self):
        return self.escape

    def quoted(self):
        return self.quote

    def missing_quote(self):
        return self.quote if self.unterminated_quote else None

    # Internal

    def compute_unadorned(self):
        if self.original is not None:
            self.escape = False
            self.unterminated_quote = False
            if self[0] in StringLiteral.QUOTES:
                # Remove quotes
                self.quote = self[0]
                self.unterminated_quote = self[-1] != self.quote
                self.string = self[1:] if self.unterminated_quote else self[1:-1]
            else:
                # Remove escapes if any
                self.string = ''
                i = 0
                n = len(self)
                while i < n:
                    c = self[i]
                    i += 1
                    if c == '\\':
                        self.escape = True
                        if i < n:
                            c = self[i]
                            i += 1
                            self.string += c
                        else:
                            raise Exception(f'string literal terminated by lone escape: {self}')
                    else:
                        self.string += c
