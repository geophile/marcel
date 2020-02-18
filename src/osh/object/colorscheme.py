class Color:

    def __init__(self, r, g, b, bold=False):
        self.r = r
        self.g = g
        self.b = b
        self.bold = bold
        # See https://unix.stackexchange.com/questions/124407/what-color-codes-can-i-use-in-my-ps1-prompt
        self.code = 16 + r * 36 + g * 6 + b


bold = True
white = Color(5, 5, 5)
white_bold = Color(5, 5, 5, bold)
red = Color(5, 0, 0)
red_bold = Color(5, 0, 0, bold)
green = Color(0, 5, 0)
green_bold = Color(0, 5, 0, bold)
blue = Color(0, 0, 5)
blue_bold = Color(0, 0, 5, bold)


class ColorScheme:

    def __init__(self):
        self.prompt_shell_indicator = None
        self.prompt_who = None
        self.prompt_dir = None
        self.prompt_separator = None
        self.file_file = None
        self.file_dir = None
        self.file_link = None
        self.file_extension = {}
        self.process_pid = None
        self.process_commandline = None
        self.error = None



