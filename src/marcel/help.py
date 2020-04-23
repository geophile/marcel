import textwrap

# Markup:
#
# - {}: highlight term being defined, e.g. a flag.
#
# - b{}: bold.
#
# - i{}: italic.
#
# - n{}: highlighting meant to indicate a name, e.g. of a class or builtin type.
#
# - indented text: don't wrap
#
# - Blank lines are preserved
#
# Markup may include any text other than { and }, including whitespace. Markup must be adjacent to whitespace
# on the left, and anything on the right.


class Markup:

    MARKUP_PREFIX = 'bin'

    def __init__(self, text, start, preceding_non_ws_count, color_scheme):
        self.start = start
        self.end = text.find('}', start) + 1
        self.preceding_non_ws_count = preceding_non_ws_count
        if self.end == -1:
            raise Exception()
        # Compute non-ws count for bracketed text
        self.non_ws_count = 0
        p = start + Markup.start_size(text, start)
        while p < self.end - 1:
            if not text[p].isspace():
                self.non_ws_count += 1
            p += 1
        start_size = self.start_size(text, start)
        self.content = text[self.start + start_size:self.end - 1]
        self.color = (color_scheme.help_highlight if start_size == 1 else
                      color_scheme.help_bold if text[start] == 'b' else
                      color_scheme.help_italic if text[start] == 'i' else
                      color_scheme.help_name)

    def __repr__(self):
        return f'({self.preceding_non_ws_count} : {self.content} : {self.non_ws_count})'

    def size(self):
        return self.end - self.start

    @staticmethod
    def start_size(text, p):
        return (1 if text[p] == '{' else
                2 if text[p] in Markup.MARKUP_PREFIX and len(text) > p + 1 and text[p + 1] == '{' else
                0)

    @staticmethod
    def starts_here(text, p):
        return Markup.start_size(text, p) > 0


class Block:

    def remove_markup(self):
        assert False

    def wrap(self):
        assert False

    def format(self):
        assert False


class EmptyLine(Block):

    def __repr__(self):
        return ''

    def remove_markup(self):
        pass

    def wrap(self):
        pass

    def format(self):
        return ''


class Paragraph(Block):

    def __init__(self, help_text):
        self.help_text = help_text
        self.lines = []
        self.markup = None
        self.plaintext = None
        self.wrapped = None
        self.wrapper = textwrap.TextWrapper(break_long_words=False)

    def __repr__(self):
        return '\n'.join(self.lines)

    def append(self, line):
        self.lines.append(line)

    def remove_markup(self):
        self.markup = []
        self.plaintext = ''
        text = '\n'.join(self.lines)
        n = len(text)
        non_ws_count = 0
        p = 0
        while p < n:
            if Markup.starts_here(text, p):
                markup = Markup(text, p, non_ws_count, self.help_text.color_scheme)
                self.markup.append(markup)
                non_ws_count += markup.non_ws_count
                self.plaintext += markup.content
                p += markup.size()  # includes the markup notation itself
            else:
                if not text[p].isspace():
                    non_ws_count += 1
                self.plaintext += text[p]
                p += 1

    def wrap(self):
        self.wrapped = self.wrapper.fill(self.plaintext)

    def format(self):
        formatted = ''
        text = self.wrapped
        n = len(text)
        p = 0  # position in text
        format_function = self.help_text.format_function
        m = 0  # markup index
        non_ws_count = 0
        while p < n and m < len(self.markup):
            markup = self.markup[m]
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
            # Process markup
            formatted += format_function(markup.content, markup.color)
            p += len(markup.content)
            non_ws_count += markup.non_ws_count
            m += 1
        formatted += text[p:]
        return formatted


class IndentedLine(Paragraph):

    def __init__(self, line, help_text):
        super().__init__(help_text)
        super().append(line)

    def __repr__(self):
        return self.lines[0]

    def wrap(self):
        self.wrapped = self.plaintext


class HelpFormatter:

    def __init__(self, colorscheme, format_function):
        self.color_scheme = colorscheme
        self.format_function = format_function
        self.original = None
        self.blocks = None

    def format(self, original):
        if original is None:
            return ''
        buffer = []
        self.original = original
        self.find_blocks()
        for block in self.blocks:
            block.remove_markup()
            block.wrap()
            buffer.append(block.format())
        return '\n'.join(buffer)
        
    def find_blocks(self):
        self.blocks = []
        paragraph = None
        for line in self.original.split('\n'):
            if len(line) == 0:
                self.blocks.append(EmptyLine())
                paragraph = None
            elif line[0].isspace():
                self.blocks.append(IndentedLine(line, self))
                paragraph = None
            else:
                if paragraph is None:
                    paragraph = Paragraph(self)
                    self.blocks.append(paragraph)
                paragraph.append(line)
