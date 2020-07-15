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

import textwrap

import marcel.util

# Text to be formatted consists of lines grouped into paragraphs.
# Paragraphs boundaries are implicit, or explicit, using markup.
# In either case, a paragraph has attributes controlling its
# wrapping and indenting. Within a paragraph, markup can be used to
# format text.
#
# Markup syntax is {FORMAT[:TEXT]}. The optional :TEXT is present within
# a paragraph only. Without :TEXT, the markup specifies paragraph
# formatting. FORMAT strings are case-insensitive.
#
# Paragraph boundaries:
#
# A paragraph is a sequence of lines, delimited by paragraph boundaries.
# {p} and {L} can be used to introduce explicit paragraph boundaries.
# In addition, a paragraph boundary is inferred where an empty line is
# adjacent to a non-empty line. An inferred paragraph boundary
# has default properties (indent = 0, wrap = True).
#
# A line containing only whitespace and paragraph markup only is ignored.
# It does not count as a line in the paragraph on either side.
#
# Paragraph formatting:
#
# FORMAT is one of:
#
#     - p[,indent=int][,wrap[=bool]]: Indicates a text paragraph. The
#       default value of indent is 0. The default value of wrap is
#       T, (boolean values are indicated by T for true, and F for false).
#
#     - L[,indent=int[:int]][,wrap[=bool]]: Indicates a multi-line
#       list item. The default indent is 4:6. If two indents are specified,
#       the first int is for the first line of the paragraph, and the
#       second int is for subsequent lines. The default value of wrap is True.
#
# Text formatting:
#
# The opening and closing braces must occur in the same paragraph.
# FORMAT is one of:
#
#     - r: Indicates a reference to an item being described, e.g a flag
#       in an op's help.
#
#     - b: bold. Useful for section titles.
#
#     - i: italic. Useful for introducing terminology.
#
#     - n: name. Highlighting a name defined in some other document,
#       e.g. an object or op that is relevant to the topic at hand, but
#       discussed in detail elsewhere.
#
#     - cRGB[bi]: color, where RGB values are 0..5, and bi are flags for
#       bold, italic
#
# The implementation treats paragraph and text markup separately. Paragraph markup is noted and used to define and
# format paragraphs. Text markup positions are noted and removed. After wrapping and indenting, colorization is
# performed using the positions recorded previously. Position is identified by the number of non-whitespace characters
# preceding the markup. THIS MEANS THAT MARKUP MUST NOT INTRODUCE NON-WHITESPACE TEXT. This constrains the design of
# the markup language. E.g., there can't be a list formatting markup item that introduces list markup text (bullets or
# numbers). This is fixable, but then the non-whitespace counters would need to be adjusted.


MARKUP_OPEN = -1
MARKUP_CLOSE = -2
TEXTP_END = -3


# Don't want this caught. This exception should not occur during runtime, since the erroneous
# text is basically buggy source code.
class InvalidMarkupException(BaseException):

    def __init__(self, text=None):
        super().__init__(text)


class TextPointer:

    def __init__(self, text):
        self.text = text
        self.n = len(text)  # Includes escape chars
        self.p = 0
        self.nonws = 0  # non-whitespace count up to and not including p

    def __repr__(self):
        sample = self.text[self.p:min(self.p + 10, self.n)]
        return f'TextPointer(@{self.p}: {sample}...)'

    def __eq__(self, other):
        return self.p == other.p

    def __ne__(self, other):
        return self.p != other.p

    def __lt__(self, other):
        return self.p < other.p

    def __le__(self, other):
        return self.p <= other.p

    def __gt__(self, other):
        return self.p > other.p

    def __ge__(self, other):
        return self.p >= other.p

    def copy(self):
        copy = TextPointer(self.text)
        copy.p = self.p
        copy.nonws = self.nonws
        return copy

    def peek(self):
        try:
            c = self.text[self.p]
            if c == '{':
                return MARKUP_OPEN
            elif c == '}':
                return MARKUP_CLOSE
            elif c == '\\':
                c = self.text[self.p + 1]
            return c
        except IndexError:
            return TEXTP_END

    def next(self):
        try:
            c = self.text[self.p]
            self.p += 1
            if c == '{':
                return MARKUP_OPEN
            elif c == '}':
                return MARKUP_CLOSE
            elif c == '\\':
                c = self.text[self.p]
                self.p += 1
            if not c.isspace():
                self.nonws += 1
            return c
        except IndexError:
            return TEXTP_END

    def at_end(self):
        return self.p >= self.n

    def non_whitespace_count(self):
        return self.nonws

    def advance_past(self, c):
        assert TextPointer.is_markup_boundary(c) or (type(c) is str and len(c) == 1), c
        next = self.next()
        while next != c and next != TEXTP_END:
            next = self.next()

    def advance_to(self, c):
        self.advance_past(c)
        self.backup()

    def set(self, other):
        self.text = other.text
        self.n = other.n
        self.p = other.p
        self.nonws = other.nonws

    def contents(self):
        return self.text[self.p:]

    def contents_to(self, end):
        assert self.text is end.text
        return self.text[self.p:end.p]

    def snippet(self, n):
        return self.text[self.p:min(self.p + n, len(self.text))]

    def backup(self):
        if self.p == 0:
            raise Exception(f'Cannot backup {self}, at the beginning.')
        if self.p >= self.n:
            self.p = self.n
        self.p -= 1
        if not self.text[self.p].isspace():
            self.nonws -= 1
        if self.p > 0 and self.text[self.p - 1] == '\\':
            self.p -= 1
        return self

    @staticmethod
    def is_markup_boundary(x):
        return x == MARKUP_OPEN or x == MARKUP_CLOSE


class Markup:

    def __init__(self, text):
        self.text = text
        if not (text[0] == '{' and text[-1] == '}'):
            self.raise_invalid_markup()

    def __repr__(self):
        return self.text

    def raise_invalid_markup(self):
        try:
            raise InvalidMarkupException(self.text)
        except AttributeError:
            # Subclass ran into trouble before Markup.__init__ could supply text.
            raise InvalidMarkupException()


class ParagraphMarkup(Markup):

    def __init__(self, text):
        super().__init__(text)
        self.code = None
        self.indent1 = None
        self.indent2 = None
        self.wrap = None
        self.parse_paragraph_formatting()

    def parse_paragraph_formatting(self):
        parts = self.text[1:-1].split(',')
        self.code = parts[0].lower()
        if len(self.code) > 1:
            self.raise_invalid_markup()
        assert self.code in 'pl', self.code
        for part in parts[1:]:
            tokens = part.split('=')
            if len(tokens) == 1:
                if tokens[0].lower() == 'wrap':
                    self.wrap = True
                else:
                    self.raise_invalid_markup()
            elif len(tokens) == 2:
                key, value = tokens
                key = key.lower()
                if key == 'indent':
                    try:
                        indents = [int(x) for x in value.split(':')]
                        if len(indents) < 1 or len(indents) > 2:
                            self.raise_invalid_markup()
                        self.indent1 = indents[0]
                        self.indent2 = indents[1] if len(indents) > 1 else self.indent1
                    except ValueError:
                        self.raise_invalid_markup()
                elif key == 'wrap':
                    self.wrap = value.lower() == 't'
            else:
                self.raise_invalid_markup()
        if self.indent1 is None:
            self.indent1, self.indent2 = (0, 0) if self.code == 'p' else (4, 6)
        if self.wrap is None:
            self.wrap = True


class TextMarkup(Markup):

    def __init__(self, textp, preceding_non_ws_count, color_scheme):
        try:
            self.markup_start = textp.copy()
            assert self.markup_start.peek() == MARKUP_OPEN
            self.preceding_non_ws_count = preceding_non_ws_count
            # Parse the formatting, and get past the colon
            self.color, text_start = self.formatting(textp, color_scheme)
            # Find the closing } of the markup, and count non-whitespace characters
            textp = text_start.copy()
            self.non_ws_count = 0
            close = None
            self.content = ''
            while not textp.at_end() and close is None:
                c = textp.next()
                if c == MARKUP_CLOSE:
                    close = textp.copy()
                elif c == MARKUP_OPEN or c == TEXTP_END:
                    self.raise_invalid_markup()
                else:
                    assert type(c) is str, c
                    self.content += c
                    if not c.isspace():
                        self.non_ws_count += 1
            if close is None:
                self.text = text_start.snippet(10)  # For exception message
                self.raise_invalid_markup()
            self.markup_end = close.copy()
        except InvalidMarkupException:
            # super hasn't been initialized, so super's raise_invalid_markup can't describe what the problem is.
            raise InvalidMarkupException(self.markup_start.snippet(10))
        super().__init__(self.markup_start.contents_to(self.markup_end))

    def __repr__(self):
        return f'({self.preceding_non_ws_count} : {self.text} : {self.non_ws_count})'

    def formatting(self, textp, color_scheme):
        assert textp.next() == MARKUP_OPEN
        color = None
        try:
            c = textp.next()
            if c in ('b', 'B', 'i', 'I', 'n', 'N', 'r', 'R'):
                c = c.lower()
                if textp.next() != ':':
                    self.raise_invalid_markup()
                if c == 'r':
                    color = color_scheme.help_reference
                elif c == 'b':
                    color = color_scheme.help_bold
                elif c == 'i':
                    color = color_scheme.help_italic
                elif c == 'n':
                    color = color_scheme.help_name
            elif c in ('c', 'C'):
                r = int(textp.next())
                g = int(textp.next())
                b = int(textp.next())
                # Look for the colon, make sure it is at a plausible distance.
                colon = textp.copy()
                colon.advance_to(':')
                style_spec = textp.contents_to(colon)
                if len(style_spec) > 2:
                    self.raise_invalid_markup()
                style = 0
                for x in style_spec:
                    x = x.lower()
                    if x == 'b':
                        style = style | color_scheme.bold()
                    elif x == 'i':
                        style = style | color_scheme.italic()
                    else:
                        self.raise_invalid_markup()
                color = color_scheme.color(r, g, b, style)
                textp = colon
                textp.next()  # Get past the colon
            else:
                self.raise_invalid_markup()
            return color, textp.copy()
        except ValueError:
            self.raise_invalid_markup()
        except IndexError:
            self.raise_invalid_markup()

    @staticmethod
    def starts_here(text, p):
        return text[p] == '{' and (p == 0 or text[p - 1] != '\\')


class Paragraph:
    BLANK_LINE = ''
    DEFAULT_MARKUP = '{p}'

    def __init__(self, help_formatter, markup=DEFAULT_MARKUP):
        self.help_formatter = help_formatter
        self.lines = []
        self.paragraph_markup = ParagraphMarkup(markup)
        self.text_markup = None
        self.plaintext = None
        self.wrapped = None
        self.indented = None

    def __repr__(self):
        text = '\n'.join(self.lines)
        return f'{self.paragraph_markup}[{text}]'

    def append(self, line):
        line = Paragraph.normalize(line)
        if len(self.lines) == 0 or (self.lines[-1] is Paragraph.BLANK_LINE) == (line is Paragraph.BLANK_LINE):
            self.lines.append(line)
            return True
        else:
            return False

    def remove_markup(self):
        self.text_markup = []
        self.plaintext = ''
        text = '\n'.join(self.lines)
        textp = TextPointer(text)
        non_ws_count = 0
        while not textp.at_end():
            c = textp.peek()
            if c == MARKUP_OPEN:
                markup = TextMarkup(textp, non_ws_count, self.help_formatter.color_scheme)
                self.text_markup.append(markup)
                non_ws_count += markup.non_ws_count
                self.plaintext += markup.content
                textp = markup.markup_end.copy()
            elif c == MARKUP_CLOSE or c == TEXTP_END:
                pass
            else:
                assert type(c) is str
                if not c.isspace():
                    non_ws_count += 1
                self.plaintext += c
                textp.next()

    def wrap(self):
        if self.paragraph_markup.wrap:
            # Trim lines. textwrap.wrap should do this (based on my understanding of the docs)
            # but doesn't seem to.
            self.trim_lines_to_be_wrapped()
            wrapper = textwrap.TextWrapper(width=self.help_formatter.help_columns,
                                           break_long_words=False,
                                           break_on_hyphens=False,
                                           initial_indent=' ' * self.paragraph_markup.indent1,
                                           subsequent_indent=' ' * self.paragraph_markup.indent2)
            self.wrapped = '\n'.join(wrapper.wrap(self.plaintext))
        else:
            self.wrapped = ' ' * self.paragraph_markup.indent1 + self.plaintext

    def trim_lines_to_be_wrapped(self):
        trimmed = []
        for line in self.plaintext.split('\n'):
            trimmed.append(line.strip())
        self.plaintext = ' '.join(trimmed)

    def format(self):
        formatted = ''
        text = self.wrapped
        n = len(text)
        p = 0  # position in text
        format_function = self.help_formatter.format_function
        m = 0  # markup index
        non_ws_count = 0
        while p < n and m < len(self.text_markup):
            markup = self.text_markup[m]
            while non_ws_count < markup.preceding_non_ws_count:
                c = text[p]
                p += 1
                formatted += c
                if not c.isspace():
                    non_ws_count += 1
            # There may be some whitespace
            while text[p].isspace():
                formatted += text[p]
                p += 1
            # Process markup. Don't use markup.context, as formatting may have modified it (bug 39).
            markup_text = ''
            markup_non_ws_count = 0
            while markup_non_ws_count < markup.non_ws_count:
                c = text[p]
                p += 1
                markup_text += c
                if not c.isspace():
                    markup_non_ws_count += 1
            formatted += format_function(markup_text, markup.color)
            non_ws_count += markup_non_ws_count
            m += 1
        formatted += text[p:]
        return formatted

    @staticmethod
    def normalize(line):
        return Paragraph.BLANK_LINE if len(line.strip()) == 0 else line


class HelpFormatter:
    RIGHT_MARGIN = 0.10

    def __init__(self, color_scheme, format_function=marcel.util.colorize):
        self.color_scheme = color_scheme
        self.format_function = format_function
        self.help_columns = None

    def format(self, text):
        self.find_console_width()
        if text is None:
            return None
        blocks = self.find_explicit_paragraph_boundaries(text)
        paragraphs = self.make_implicit_paragraph_boundaries_explicit(blocks)
        buffer = []
        for paragraph in paragraphs:
            paragraph.remove_markup()
            paragraph.wrap()
            buffer.append(paragraph.format())
        return '\n'.join(buffer)

    # Input: marked-up text
    # Output: List of text blocks interspersed with Paragraphs from paragraph markup ({p}, {L}).
    def find_explicit_paragraph_boundaries(self, text):
        blocks = []
        textp = TextPointer(text)
        while not textp.at_end():
            open, close = HelpFormatter.find_paragraph_markup(textp)
            if open.at_end():
                blocks.append(textp.contents())
                textp = open
            else:
                if textp < open:
                    blocks.append(textp.contents_to(open))
                blocks.append(Paragraph(self, open.contents_to(close)))
                # Skip whitespace after close, up to and including the first \n
                textp = close
                c = textp.next()
                while type(c) is str and c.isspace() and c != '\n':
                    c = textp.next()
                if c != '\n':
                    textp.backup()
        return blocks

    # Input: Array of text blocks and Paragraphs.
    # Output: Array of Paragraphs. A text block may give rise to multiple Paragraphs due to implicit boundaries.
    def make_implicit_paragraph_boundaries_explicit(self, blocks):
        paragraphs = []
        n = len(blocks)
        paragraph = None
        # Make sure first paragraph is marked
        if n > 0 and not isinstance(blocks[0], Paragraph):
            paragraph = Paragraph(self)
            paragraphs.append(paragraph)
        b = 0
        while b < n:
            block = blocks[b]
            b += 1
            if isinstance(block, Paragraph):
                paragraph = block
                paragraphs.append(paragraph)
            else:
                lines = block.split('\n')
                if HelpFormatter.ignore(lines[-1]):
                    del lines[-1]
                for line in lines:
                    appended = paragraph.append(line)
                    if not appended:
                        # Line rejected because it doesn't match the lines of the current paragraph.
                        # Start a new one.
                        paragraph = Paragraph(self)
                        paragraphs.append(paragraph)
                        appended = paragraph.append(line)
                        assert appended
        return paragraphs

    def find_console_width(self):
        console_columns = marcel.util.console_width()
        if console_columns is None:
            console_columns = 70  # Default for textwrap module
        self.help_columns = int((1 - HelpFormatter.RIGHT_MARGIN) * console_columns)

    @staticmethod
    def find_paragraph_markup(textp):
        open = textp.copy()
        open.advance_past(MARKUP_OPEN)
        while not open.at_end() and not open.peek() in ('p', 'P', 'l', 'L'):
            open.advance_past(MARKUP_OPEN)
        if open.at_end():
            return open, None
        close = open.copy()
        close.advance_past(MARKUP_CLOSE)
        if close.at_end():
            raise Exception(f'Unterminated markup starting at {open}')
        return open.backup(), close

    # ignore if all whitespace without \n
    @staticmethod
    def ignore(s):
        return len(s) == 0 or s.isspace() and s.count('\n') == 0
