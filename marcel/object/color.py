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

import sys

import marcel.exception
import marcel.object.renderable
import marcel.util


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
        bold = self.bold() != 0
        italic = self.italic() != 0
        style = (', BOLD | ITALIC' if bold and italic else
                 ', BOLD' if bold else
                 ', ITALIC' if italic else
                 '')
        return f'Color({self.r}, {self.g}, {self.b}{style})'

    def bold(self):
        return self.style & Color.BOLD != 0

    def italic(self):
        return self.style & Color.ITALIC != 0


class ColorSchemeError(marcel.exception.KillShellException):

    def __init__(self, message):
        super().__init__(message)


class ColorScheme(marcel.object.renderable.Renderable):

    KEYS = sorted([
        'color_scheme_key',
        'color_scheme_value',
        'file_file',
        'file_dir',
        'file_link',
        'file_link_broken',
        'file_executable',
        'file_extension',
        'process_pid',
        'process_ppid',
        'process_status',
        'process_user',
        'process_command',
        'error',
        'help_reference',
        'help_bold',
        'help_italic',
        'help_name',
        'history_id',
        'history_command'
    ])

    def __init__(self):
        for key in ColorScheme.KEYS:
            setattr(self, key, None)

    def __repr__(self):
        buffer = []
        for k in ColorScheme.KEYS:
            buffer.append(f'{k}: {self.__dict__[k]}')
        return '{' + ', '.join(buffer) + '}'

    def __setattr__(self, key, value):
        if key not in ColorScheme.KEYS:
            raise ColorSchemeError(f'{key} is not a supported color scheme attribute.')
        if value is not None and type(value) not in (Color, dict):
            raise ColorSchemeError(f'Can only set color scheme attribute to a Color, '
                                   f'key: {key}, value type: {type(value)}')
        if type(value) is dict:
            for ext, color in value.items():
                if type(color) is not Color:
                    raise ColorSchemeError(f'Can only set color for an extension to a Color, '
                                           f'extension: {ext}, value type: {type(color)}')
        self.__dict__[key] = value

    def set_color(self, key, value):
        setattr(self, key, value)
        return value

    def set_extension_color(self, ext, value):
        getattr(self, 'file_extension')[ext] = value
        return value

    def render_full(self, color_scheme):
        def colorize(s, color_name):
            return marcel.util.colorize(s, getattr(color_scheme, color_name))
        kv = []
        n = 0
        for k in ColorScheme.KEYS:
            n += 1
            comma = ',' if n < len(self.__dict__) else ''
            v = self.__dict__[k]
            if type(v) is dict:
                kv.append(f'    {colorize(k, "color_scheme_key")}: {{')
                vn = 0
                for vk in sorted(v):
                    vn += 1
                    v_comma = ',' if vn < len(v) else ''
                    vv = v[vk]
                    kv.append(f'        {colorize(vk, "color_scheme_key")}: {colorize(vv, "color_scheme_value")}{v_comma}')
                kv.append(f'    }}{comma}')
            else:
                kv.append(f'    {colorize(k, "color_scheme_key")}: {colorize(v, "color_scheme_value")}{comma}')
        contents = '\n'.join(kv)
        return '{\n' + contents + '\n}'

    def color(self, r, g, b, style):
        return Color(r, g, b, style)

    def bold(self):
        return Color.BOLD

    def italic(self):
        return Color.ITALIC
