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

    def __repr__(self):
        style = ''
        if self.bold() != 0:
            style += 'b'
        if self.italic() != 0:
            style += 'i'
        return f'C{self.r}{self.g}{self.b}{style}'

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
        self.process_ppid = None
        self.process_state = None
        self.process_user = None
        self.process_commandline = None
        self.error = None
        self.help_reference = None
        self.help_bold = None
        self.help_italic = None
        self.help_name = None
        self.history_id = None
        self.history_command = None

    def color(self, r, g, b, style):
        return Color(r, g, b, style)

    def bold(self):
        return Color.BOLD

    def italic(self):
        return Color.ITALIC
