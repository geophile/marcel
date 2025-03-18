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

import os
import pathlib

from prompt_toolkit.completion import Completer, Completion

import marcel.core
import marcel.doc
import marcel.exception
import marcel.op
import marcel.parser
import marcel.util

DEBUG = False

SINGLE_QUOTE = "'"
DOUBLE_QUOTE = '"'
QUOTES = SINGLE_QUOTE + DOUBLE_QUOTE
NL = '\n'


def debug(message):
    if DEBUG:
        print(message, flush=True)


class TabCompleter(Completer):

    OPS = marcel.op.public
    HELP_TOPICS = list(marcel.doc.topics) + OPS

    def __init__(self, env):
        self.env = env
        self.parser = None

    def get_completions(self, document, complete_event):
        debug(f'get_completions: doc=<{document}> ------------------------------------------------------------')
        token = self.parse(document.text)
        last_token_context = self.parser.op_arg_context
        if last_token_context.is_op():
            completer = self.complete_op
        elif last_token_context.is_flag():
            completer = self.complete_flag
        elif last_token_context.is_arg():
            completer = self.complete_arg
        else:
            assert False, last_token_context
        for c in completer(token):
            yield c

    # Returns the last token encountered by the parse of line
    def parse(self, line):
        # Parse the text so far, to get information needed for tab completion. It is expected that
        # the text will end early, since we are doing tab completion here. This results in a PrematureEndError
        # which can be ignored. The important point is that the parse will set Parser.op.
        self.parser = marcel.parser.Parser(line, self.env)
        try:
            self.parser.parse()
        except marcel.exception.MissingQuoteException as e:
            debug(f'Caught MissingQuoteException: <{e.quote}{e.unterminated_string}>')
        except marcel.exception.KillCommandException as e:
            # Parse may have failed because of an unrecognized op, for example. Normal continuation should
            # do the right thing.
            debug(f'Caught KillCommandException: {e}')
        except BaseException as e:
            debug(f'Something went wrong: {e}')
            marcel.util.print_stack_of_current_exception()
        else:
            debug('No exception during parse')
        token = self.parser.terminal_token_value()
        # TODO: Is this logic needed? Why doesn't MissingQuoteException take care of things? Or why can't
        # TODO: this logic be moved there?
        if (missing_quote := self.parser.token.missing_quote()) is not None:
            token = missing_quote + token
        return token

    def complete_op(self, token):
        debug(f'complete_op: token={token}')
        # Include marcel ops.
        # Include executables only if there are no qualifying ops.
        found_op = False
        for op in TabCompleter.OPS:
            if len(token) == 0 or op.startswith(token):
                yield TabCompleter.completion(token, op)
                found_op = True
        if not found_op:
            for exe in TabCompleter.executables():
                if exe.startswith(token):
                    yield TabCompleter.completion(token, exe)

    def complete_flag(self, token):
        debug(f'complete_flag: token={token}')
        for flag in self.parser.flags():
            if flag.startswith(token):
                yield TabCompleter.completion(token, flag)

    # Arg completion assumes we're looking for filenames. (bash does this too.)
    def complete_arg(self, token):
        debug(f'complete_arg: token={token}')
        current_dir = self.env.dir_state().current_dir()
        for filename in TabCompleter.complete_filename(current_dir, token):
            yield TabCompleter.completion(token, filename)

    @staticmethod
    def complete_help(text):
        debug(f'complete_help, text = <{text}>')
        candidates = []
        for topic in TabCompleter.HELP_TOPICS:
            if topic.startswith(text):
                candidates.append(topic)
        debug(f'complete_help candidates for <{text}>: {candidates}')
        return candidates


    @staticmethod
    def op_name(line):
        first = line.split()[0]
        return first if first in TabCompleter.OPS else None

    @staticmethod
    def executables():
        executables = []
        path = os.environ['PATH'].split(':')
        for p in path:
            for f in os.listdir(p):
                if marcel.util.is_executable(f) and f not in executables:
                    executables.append(f)
        return executables

    @staticmethod
    def completion(token, completion):
        return Completion(text=f'{completion[len(token):]} ',
                          display=completion)

    @staticmethod
    def complete_filename(current_dir, token):
        debug(f'complete_filename: current_dir=<{current_dir}>, token=<{token}>')
        def add_slash_to_dir(f):
            return f + '/' if pathlib.Path(f).expanduser().is_dir() else f

        filenames = []
        if token:
            if (quote := token[0]) in '"\'':
                unquoted = token[1:]
                # TODO: This is too simplistic. In '~/...' and ~/... the ~ is expanded. But not in "~/...".
                for filename in TabCompleter.complete_filename(current_dir, unquoted):
                    filenames.append(f'{quote}{filename}{quote}')
            if token.startswith('~/'):
                if token == '~/':
                    home = pathlib.Path(token).expanduser()
                    for filename in os.listdir(home.as_posix()):
                        filenames.append(add_slash_to_dir(filename))
                elif token.startswith('~/'):
                    base = pathlib.Path('~/').expanduser()
                    base_length = len(base.as_posix())
                    pattern = token[2:] + '*'
                    for filename in [p.as_posix() for p in base.glob(pattern)]:
                        filenames.append(add_slash_to_dir('~' + filename[base_length:]))
            elif token.startswith('~'):
                find_user = token[1:]
                for username in TabCompleter.usernames():
                    if username.startswith(find_user):
                        filenames.append(add_slash_to_dir('~' + username))
            elif token.startswith('/'):
                base = '/'
                pattern_prefix = token[1:]
                for path in pathlib.Path(base).glob(pattern_prefix + '*'):
                    filenames.append(add_slash_to_dir(path.as_posix()))
            else:
                base = current_dir
                pattern_prefix = token
                for path in pathlib.Path(base).glob(pattern_prefix + '*'):
                    filenames.append(add_slash_to_dir(path.relative_to(base).as_posix()))
        else:
            # All filenames in current directory
            for path in current_dir.iterdir():
                filenames.append(add_slash_to_dir(path.relative_to(current_dir).as_posix()))
        return sorted(filenames)

    @staticmethod
    def usernames():
        usernames = []
        # TODO: Is this portable, even across UNIXes?
        with open('/etc/passwd', 'r') as passwds:
            users = passwds.readlines()
        for line in users:
            fields = line.split(':')
            username = fields[0]
            usernames.append(username)
        return usernames
