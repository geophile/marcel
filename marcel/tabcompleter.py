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
import os.path
import pathlib
import readline

import marcel.core
import marcel.doc
import marcel.exception
import marcel.op
import marcel.parser
import marcel.util

Parser = marcel.parser.Parser


DEBUG = False


def debug(message):
    if DEBUG:
        print(message, flush=True)


class TabCompleter:

    OPS = marcel.op.public
    HELP_TOPICS = list(marcel.doc.topics) + OPS

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
        candidates = self.candidates(readline.get_line_buffer(), text)
        return candidates[state] if candidates else None

    def complete_op(self, text):
        debug(f'complete_op, text = <{text}>')
        candidates = []
        if len(text) > 0:
            # Display marcel ops.
            # Display executables only if there are no qualifying ops.
            for op in TabCompleter.OPS:
                if op.startswith(text):
                    candidates.append(op)
            if len(candidates) == 0:
                self.ensure_executables()
                for ex in self.executables:
                    if ex.startswith(text):
                        candidates.append(ex)
            debug(f'complete_op candidates for {text}: {candidates}')
        else:
            candidates = TabCompleter.OPS
        # Append a space if there is only one candidate
        if len(candidates) == 1:
            candidates = [candidates[0] + ' ']
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

    @staticmethod
    def complete_flag(text, flags):
        candidates = []
        for f in flags:
            if f.startswith(text):
                candidates.append(f)
        debug('complete_flag candidates for <{}>: {}'.format(text, candidates))
        if len(candidates) == 1:
            candidates = [candidates[0] + ' ']
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
            filenames = [p.relative_to(current_dir).as_posix() for p in current_dir.iterdir()]
        filenames = [f + '/' if os.path.isdir(f) else f for f in filenames]
        if len(filenames) == 1:
            if not filenames[0].endswith('/'):
                filenames = [filenames[0] + ' ']
        debug('complete_filename candidates for {}: {}'.format(text, filenames))
        return filenames

    def candidates(self, line, text):
        candidates = None
        debug(f'complete: line={line}, text=<{text}>')
        if len(line.strip()) == 0:
            candidates = TabCompleter.OPS
        else:
            # Parse the text so far, to get information needed for tab completion. It is expected that
            # the text will end early, since we are doing tab completion here. This results in a PrematureEndError
            # which can be ignored. The important point is that the parse will set Parser.op.
            parser = marcel.parser.Parser(line, self.main)
            try:
                parser.parse()
                debug(f'parse succeeded, context: {parser.tab_completion_context}')
            except Exception as e:
                debug(f'caught {type(e)}: {e}')
                # Don't do tab completion
                candidates = None
                return
            except marcel.exception.KillCommandException as e:
                # Parse may have failed because of an unrecognized op, for example. Normal continuation should
                # do the right thing.
                debug(f'Caught KillCommandException: {e}')
            except BaseException as e:
                debug(f'Something went really wrong: {e}')
                marcel.util.print_stack()
            context = parser.tab_completion_context
            if context.is_complete_op():
                op = context.op()
                if op is None:
                    # Could be a partial op name, an executable name (or partial), or just gibberish
                    candidates = self.complete_op(text)
                elif op.op_name() == 'help':
                    candidates = self.complete_help(text)
                else:
                    # Could be a partial op name, an executable name (or partial), or just gibberish
                    candidates = self.complete_op(text)
            elif context.is_complete_arg():
                if len(text) == 0:
                    candidates = self.complete_filename(text)
                elif text[-1].isspace():
                    text = ''
                    candidates = self.complete_filename(text)
                elif text.startswith('-'):
                    candidates = self.complete_flag(text, context.flags())
                else:
                    candidates = self.complete_filename(text)
        return candidates

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
                    if marcel.util.is_executable(f) and f not in self.executables:
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

