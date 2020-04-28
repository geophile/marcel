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
#     - L[,indent=int][,mark=char][,wrap[=bool]]: Indicates a multi-line
#       list item. The default indent is 4. The default list marker is '-'.
#       The default value of wrap is True. The first line of the paragraph
#       will be indented by the indicated amount. Following the indent is
#       the mark character, a space, and then the first line of text appears.
#       Subsequent lines will be indented by two additional characters, so that
#       the text lines up with the beginning of text on the first line of the
#       paragraph.
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


class Markup:

    def __init__(self, text):
        if not (text[0] == '{' and text[-1] == '}'):
            self.raise_invalid_formatting_exception()
        self.text = text

    def __repr__(self):
        return self.text

    def raise_invalid_formatting_exception(self):
        raise Exception(f'Invalid formatting specification: {self.text}')


class ParagraphMarkup(Markup):

    def __init__(self, text):
        super().__init__(text)
        self.code = None
        self.indent = None
        self.mark = None
        self.wrap = None
        self.parse_paragraph_formatting()

    def parse_paragraph_formatting(self):
        parts = self.text[1:-1].split(',')
        code = parts[0].lower()
        if len(code) > 1:
            print(code)
            self.raise_invalid_formatting_exception()
        assert code in 'pl', code
        for part in parts[1:]:
            tokens = part.split('=')
            if len(tokens) == 1:
                if tokens[0].lower() == 'wrap':
                    self.wrap = True
                else:
                    self.raise_invalid_formatting_exception()
            elif len(tokens) == 2:
                key, value = tokens
                key = key.lower()
                if key == 'indent':
                    try:
                        self.indent = int(value)
                    except ValueError:
                        self.raise_invalid_formatting_exception()
                elif key == 'wrap':
                    self.wrap = value == 'T'
                elif key == 'mark':
                    if len(value) == 1:
                        self.mark = value
                    else:
                        self.raise_invalid_formatting_exception()
            else:
                self.raise_invalid_formatting_exception()
        if self.indent is None:
            self.indent = 0
        if self.wrap is None:
            self.wrap = True
        if self.code == 'p':
            if self.mark is not None:
                self.raise_invalid_formatting_exception()
        else:
            if self.mark is None:
                self.mark = '-'


class TextMarkup(Markup):

    def __init__(self, text, open, preceding_non_ws_count, color_scheme):
        close = None
        p = open + 1
        n = len(text)
        while p < n and close is None:
            if text[p] == '}' and text[p - 1] != '\\':
                close = p
            else:
                p += 1
        if close is None:
            self.text = text[open:min(open + 10, n)]  # For exception message
            self.raise_invalid_formatting_exception()
        close += 1
        super().__init__(text[open:close])
        self.size = close - open
        colon = text.find(':', open)
        if colon == -1:
            self.raise_invalid_formatting_exception()
        self.preceding_non_ws_count = preceding_non_ws_count
        self.color_scheme = color_scheme
        # Compute non-ws count for bracketed text.
        # TODO: Escaped chars
        self.non_ws_count = 0
        p = colon + 1
        while p < close - 1:
            if not text[p].isspace():
                self.non_ws_count += 1
            p += 1
        self.content = text[colon + 1:close - 1]
        self.color = self.find_color(text[open + 1:colon])

    def __repr__(self):
        return f'({self.preceding_non_ws_count} : {self.content} : {self.non_ws_count})'

    def find_color(self, format):
        code = format[0]
        color = None
        if code == 'r':
            color = self.color_scheme.help_reference
        elif code == 'b':
            color = self.color_scheme.help_bold
        elif code == 'i':
            color = self.color_scheme.help_italic
        elif code == 'n':
            color = self.color_scheme.help_name
        elif code == 'c':
            try:
                r, g, b = (int(x) for x in format[1:4])
                style = 0
                for x in format[4:].lower():
                    if x == 'b':
                        style = style | self.color_scheme.bold()
                    elif x == 'i':
                        style = style | self.color_scheme.italic()
                    else:
                        self.raise_invalid_formatting_exception()
                color = self.color_scheme.color(r, g, b, style)
            except ValueError:
                self.raise_invalid_formatting_exception()
        else:
            self.raise_invalid_formatting_exception()
        return color

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
        self.wrapper = textwrap.TextWrapper(break_long_words=False)

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
        n = len(text)
        non_ws_count = 0
        p = 0
        while p < n:
            if TextMarkup.starts_here(text, p):
                markup = TextMarkup(text, p, non_ws_count, self.help_formatter.color_scheme)
                self.text_markup.append(markup)
                non_ws_count += markup.non_ws_count
                self.plaintext += markup.content
                p += markup.size  # includes the markup notation itself
            else:
                if not text[p].isspace():
                    non_ws_count += 1
                self.plaintext += text[p]
                p += 1

    def wrap(self):
        self.wrapped = self.wrapper.fill(self.plaintext) if self.paragraph_markup.wrap else self.plaintext

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

    def __init__(self, color_scheme, format_function=marcel.util.colorize):
        self.color_scheme = color_scheme
        self.format_function = format_function

    def format(self, text):
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
        p = 0
        n = len(text)
        while p < n:
            open, close = HelpFormatter.find_paragraph_markup(text, p)
            if open == -1:
                blocks.append(text[p:])
                p = n
            else:
                if p < open:
                    blocks.append(text[p:open])
                blocks.append(Paragraph(self, text[open:close]))
                # Skip whitespace after close, up to and including the first \n
                p = close
                while p < n and text[p].isspace() and text[p] != '\n':
                    p += 1
                if p < n and text[p] == '\n':
                    p += 1
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

    @staticmethod
    def find_paragraph_markup(text, p):
        open = text.find('{', p)
        while open != -1 and not HelpFormatter.is_paragraph_markup_open(text, open):
            open = text.find('{', open + 1)
        if open == -1:
            return -1, None
        close = text.find('}', open)
        while not HelpFormatter.is_paragraph_markup_close(text, close):
            close = text.find('}', close)
        if close == -1:
            raise Exception(f'Unterminated markup at position {p}')
        return open, close + 1

    @staticmethod
    def is_paragraph_markup_open(text, p):
        assert text[p] == '{'
        if p > 0 and text[p - 1] == '\\':
            return False
        if p + 1 < len(text) and text[p + 1] in 'pPlL':
            return True

    @staticmethod
    def is_paragraph_markup_close(text, p):
        assert p > 0
        assert text[p] == '}'
        return text[p - 1] != '\\'

    # ignore if all whitespace without \n
    @staticmethod
    def ignore(s):
        return s.isspace() and s.count('\n') == 0
