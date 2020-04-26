class Color:

    def __init__(self, r, g, b, bold=False, italic=False):
        self.r = r
        self.g = g
        self.b = b
        self.bold = bold
        self.italic = italic
        # See https://unix.stackexchange.com/questions/124407/what-color-codes-can-i-use-in-my-ps1-prompt
        self.code = 16 + r * 36 + g * 6 + b

    def __str__(self):
        style = ''
        if self.bold:
            style += 'b'
        if self.italic:
            style += 'i'
        return f'Color({self.r}, {self.g}, {self.b}){style}'


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
