import sys


class Color:

    PLAIN = 0x0
    BOLD = 0x1
    ITALIC = 0x2

    def __init__(self, r, g, b, style=PLAIN):
        if min(r, g, b) < 0 or max(r, g, b) > 5 or style < 0 or style > (Color.BOLD | Color.ITALIC):
            print(f'Bad color definition (r={r}, g={g}, b={b}, style={style}', file=sys.stderr)
        self.r = r
        self.g = g
        self.b = b
        self.style = style
        # See https://unix.stackexchange.com/questions/124407/what-color-codes-can-i-use-in-my-ps1-prompt
        self.code = 16 + r * 36 + g * 6 + b

    def __str__(self):
        style = ''
        if self.bold() != 0:
            style += 'b'
        if self.italic() != 0:
            style += 'i'
        return f'Color({self.r}, {self.g}, {self.b}){style}'

    def bold(self):
        return self.style & Color.BOLD != 0

    def italic(self):
        return self.style & Color.ITALIC != 0


class ColorScheme:

    def __init__(self):
        self.prompt_shell_indicator = None
        self.prompt_who = None
        self.prompt_dir = None
        self.prompt_separator = None
        self.file_file = None
        self.file_dir = None
        self.file_link = None
        self.file_executable = None
        self.file_extension = None
        self.process_pid = None
        self.process_commandline = None
        self.error = None
        self.help_highlight = None
        self.help_bold = None
        self.help_italic = None
        self.help_name = None
