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

import os
import pathlib
import readline

import marcel.core
import marcel.doc
import marcel.exception
import marcel.op
import marcel.parser
import marcel.util


DEBUG = False


def debug(message):
    if DEBUG:
        print(message, flush=True)


class TabCompleter:

    OPS = marcel.op.public
    HELP_TOPICS = list(marcel.doc.topics) + OPS
    FILENAME_OPS = ['cat',
                    'cd',
                    'cp',
                    'emacs',
                    'less',
                    'ln',
                    'ls',
                    'mkdir',
                    'more',
                    'mv',
                    'out',
                    'rm',
                    'rmdir',
                    'vi']

    def __init__(self, main):
        self.main = main
        self.op_name = None
        self.op_flags = None
        self.executables = None
        self.homedirs = None
        readline.set_completer(self.complete)
        # Removed '-', '/', '~' from readline.get_completer_delims()
        readline.set_completer_delims(' \t\n`!@#$%^&*()=+[{]}\\|;:\'",<>?')

    def complete(self, text, state):
        line = readline.get_line_buffer()
        debug(f'complete: line={line}, text={text}')
        if len(line.strip()) == 0:
            candidates = TabCompleter.OPS
        else:
            # Parse the text so far, to get information needed for tab completion. It is expected that
            # the text will end early, since we are doing tab completion here. This results in a PrematureEndError
            # which can be ignored. The important point is that the parse will set Parser.op.
            parser = marcel.parser.Parser(line, self.main)
            try:
                parser.parse()
                debug('parse succeeded')
            except marcel.parser.PrematureEndError:
                debug('premature end')
                pass
            except Exception as e:
                debug(f'caught ({type(e)}) {e}')
                # Don't do tab completion
                return None
            except marcel.exception.KillCommandException as e:
                # Parse may have failed because of an unrecognized op, for example. Normal continuation should
                # do the right thing.
                pass
            except BaseException as e:
                debug(f'Something went really wrong: {e}')
                marcel.util.print_stack()
            op_name = parser.current_op_name
            debug(f'parser.op_name: {op_name}')
            if op_name is None:
                candidates = self.complete_op(text)
            elif op_name == 'help':
                candidates = self.complete_help(text)
            else:
                self.op_name = op_name
                self.op_flags = parser.current_op_flags
                debug(f'op_name: {self.op_name}, text: {text}')
                if text.startswith('-'):
                    candidates = self.complete_flag(text)
                elif self.is_filename_arg(parser):
                    candidates = self.complete_filename(text)
                else:
                    return None
        return candidates[state]

    def complete_op(self, text):
        debug(f'complete_op, text = <{text}>')
        candidates = []
        if len(text) > 0:
            # Display marcel ops.
            # Display executables only if there are no qualifying ops.
            for op in TabCompleter.OPS:
                op_with_space = op + ' '
                if op_with_space.startswith(text):
                    candidates.append(op_with_space)
            if len(candidates) == 0:
                self.ensure_executables()
                for ex in self.executables:
                    ex_with_space = ex + ' '
                    if ex_with_space.startswith(text):
                        candidates.append(ex_with_space)
            debug(f'complete_op candidates for {text}: {candidates}')
        else:
            candidates = TabCompleter.OPS
        return candidates

    @staticmethod
    def complete_help(text):
        debug(f'complete_help, text = <{text}>')
        candidates = []
        for topic in TabCompleter.HELP_TOPICS:
            if topic.startswith(text):
                candidates.append(topic)
        debug('complete_help candidates for <{}>: {}'.format(text, candidates))
        return candidates

    def is_filename_arg(self, parser):
        return (self.op_name in TabCompleter.FILENAME_OPS or
                self.op_name == 'bash' and parser.op.args[0] in TabCompleter.FILENAME_OPS)

    def complete_flag(self, text):
        candidates = []
        for f in self.op_flags:
            if f.startswith(text):
                candidates.append(f)
        debug('complete_flag candidates for <{}>: {}'.format(text, candidates))
        return candidates

    def complete_filename(self, text):
        debug('complete_filenames, text = <{}>'.format(text))
        current_dir = self.main.env.dir_state().pwd()
        if text:
            if text == '~/':
                home = pathlib.Path(text).expanduser()
                filenames = os.listdir(home.as_posix())
            elif text.startswith('~/'):
                base = pathlib.Path('~/').expanduser()
                base_length = len(base.as_posix())
                pattern = text[2:] + '*'
                filenames = ['~' + f[base_length:] + ' '
                             for f in [p.as_posix() for p in base.glob(pattern)]]
            elif text.startswith('~'):
                find_user = text[1:]
                self.ensure_homedirs()
                filenames = []
                for username in self.homedirs.keys():
                    if username.startswith(find_user):
                        filenames.append('~' + username + ' ')
            elif text.startswith('/'):
                base = '/'
                pattern_prefix = text[1:]
                filenames = [p.as_posix()
                             for p in pathlib.Path(base).glob(pattern_prefix + '*')]
            else:
                base = current_dir
                pattern_prefix = text
                filenames = [p.relative_to(base).as_posix()
                             for p in pathlib.Path(base).glob(pattern_prefix + '*')]
        else:
            filenames = ['/'] + [p.relative_to(current_dir).as_posix() for p in current_dir.iterdir()]
        debug('complete_filename candidates for {}: {}'.format(text, filenames))
        return filenames

    @staticmethod
    def op_name(line):
        first = line.split()[0]
        return first if first in TabCompleter.OPS else None

    def ensure_executables(self):
        if self.executables is None:
            self.executables = []
            path = os.environ['PATH'].split(':')
            for p in path:
                for f in os.listdir(p):
                    if marcel.util.is_executable(f):
                        self.executables.append(f)

    def ensure_homedirs(self):
        if self.homedirs is None:
            self.homedirs = {}
            # TODO: This is a hack. Is there a better way?
            with open('/etc/passwd', 'r') as passwds:
                users = passwds.readlines()
            for line in users:
                fields = line.split(':')
                username = fields[0]
                homedir = fields[5]
                self.homedirs[username] = homedir

