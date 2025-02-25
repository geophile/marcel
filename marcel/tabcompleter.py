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
import readline

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


# TODO: TabCompleter.complete(text, state) is called with state = 0, 1, 2, ... until None is returned, getting
#       the candidates one at a time. On each call, self.candidates() parses the line.
#       TabCompleter could keep track of the current line and the text arg. If these are the same in consecutive
#       calls, then skip the parse.

class TabCompleter(object):

    OPS = marcel.op.public
    HELP_TOPICS = list(marcel.doc.topics) + OPS

    # In completing one line of input, readline calls complete() with state = 0, 1, ... stopping when
    # complete returns None. So state = 0 indicates that we're starting a new line of input.
    # A CompletionState object is created when state = 0 is encountered, and is used until
    # complete() returns None.
    class CompletionState(object):

        def __init__(self, line):
            self.line = line
            self.completion_text = None

        def __repr__(self):
            return f'CompletionState(line = <{self.line}>, completion_text = <{self.completion_text}>)'

        def extend_completion_text(self, candidates):
            # Sanity check
            if self.completion_text:
                for candidate in candidates:
                    assert candidate.startswith(self.completion_text), (
                            f'completion text: {self.completion_text}, '
                            f'candidate: {candidate}')
            # Extend completion text
            extended_completion_text = None
            for candidate in candidates:
                if extended_completion_text is None:
                    extended_completion_text = candidate
                else:
                    for i in range(len(extended_completion_text)):
                        if extended_completion_text[i] != candidate[i]:
                            extended_completion_text = extended_completion_text[:i]
                # Keep only the new characters, not present in the input line
                extended_completion_text = extended_completion_text[len(self.line):]
                assert self.completion_text is None or self.completion_text.startswith(extended_completion_text), (
                    f'completion text: {self.completion_text}, '
                    f'extended_completion_text: {extended_completion_text}')
                self.completion_text = extended_completion_text

    def __init__(self, main):
        readline.set_completer(self.complete)
        # Removed '-', '/', '~' from readline.get_completer_delims()
        readline.set_completer_delims(' \t\n`!@#$%^&*()=+[{]}\\|;:\'",<>?')
        self.main = main
        self.completion_state = None

    # The readline completion method, registered by calling readline.set_completer()
    def complete(self, text, state):
        debug(f'complete: text=<{text}>, state={state} ------------------------------------------------------------')
        if state == 0:
            self.completion_state = TabCompleter.CompletionState(readline.get_line_buffer())
        assert self.completion_state is not None
        candidates = self.candidates(self.completion_state.line, text)
        debug(f'complete, candidates = \n{NL.join(candidates)}')
        self.completion_state.extend_completion_text(candidates)
        candidate = candidates[state] if candidates is not None and state < len(candidates) else None
        debug(f'complete, selected candidate = {candidate}')
        debug(f'complete, completion state = {self.completion_state}')
        if candidate is None:
            completion = ''
            debug(f'self.completion_state.completion_text: <{self.completion_state.completion_text}>')
            debug(f'self.completion_state.completion_text is not None: <{self.completion_state.completion_text is not None}>')
            if self.completion_state.completion_text is not None:
                # Apply completion to the displayed line: Add the completion text from CompletionState, and
                # append a space if there's only one candidate.
                completion = self.completion_state.completion_text
                debug(f'completion 1 = <{completion}>')
            debug(f'#candidates = {len(candidates)}')
            if len(candidates) == 1:
                completion += '@'
                debug(f'completion 2 = <{completion}>')
            readline.insert_text(completion)
            print(completion, end='', flush=True)
            debug(f'complete: appending <{completion}> -> <{readline.get_line_buffer()}>')
            # We're done with the current line of input
            self.completion_state = None
        return candidate

    def candidates(self, line, text):
        debug(f'candidates: line=<{line}>, text=<{text}>')
        if len(line.strip()) == 0:
            candidates = TabCompleter.OPS
        else:
            # Parse the text so far, to get information needed for tab completion. It is expected that
            # the text will end early, since we are doing tab completion here. This results in a PrematureEndError
            # which can be ignored. The important point is that the parse will set Parser.op.
            parser = marcel.parser.Parser(line, self.main.env)
            try:
                parser.parse()
            except marcel.exception.MissingQuoteException as e:
                text = e.quote + e.unterminated_string
                debug(f'Caught MissingQuoteException: <{text}>')
            except marcel.exception.KillCommandException as e:
                # Parse may have failed because of an unrecognized op, for example. Normal continuation should
                # do the right thing.
                debug(f'Caught KillCommandException: {e}')
            except Exception as e:
                debug(f'caught {type(e)}: {e}')
                # Don't do tab completion
                return
            except BaseException as e:
                debug(f'Something went really wrong: {e}')
                marcel.util.print_stack_of_current_exception()
            else:
                debug('No exception')
            debug(f'TabCompleter.candidates, is token op: {parser.expect_op()}')
            if parser.expect_op():
                op = parser.token
                candidates = (self.complete_help(text) if op.op_name == 'help' else
                              TabCompleter.complete_op(text))
            else:
                candidates = (self.complete_flag(text, parser.flags()) if text.startswith('-') else
                              self.complete_filename(text))
        return candidates

    @staticmethod
    def complete_op(text):
        debug(f'complete_op, text = <{text}>')
        candidates = []
        if len(text) > 0:
            # Display marcel ops.
            # Display executables only if there are no qualifying ops.
            for op in TabCompleter.OPS:
                if op.startswith(text):
                    candidates.append(op)
            if len(candidates) == 0:
                for ex in TabCompleter.executables():
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
        debug(f'complete_help candidates for <{text}>: {candidates}')
        return candidates

    @staticmethod
    def complete_flag(text, flags):
        candidates = []
        for f in flags:
            if f.startswith(text):
                candidates.append(f)
        debug(f'complete_flag candidates for <{text}>: {candidates}')
        if len(candidates) == 1:
            candidates = [candidates[0] + ' ']
        return candidates

    def complete_filename(self, text):
        filenames = []
        debug(f'complete_filename, text = <{text}>')
        current_dir = self.main.env.dir_state().current_dir()
        quote = None
        if text:
            # Separate quote and text if necessary
            if text[0] in QUOTES:
                quote = text[0]
                text = text[1:]
            if text.startswith('~/') and quote != DOUBLE_QUOTE:
                if text == '~/':
                    if quote != DOUBLE_QUOTE:
                        home = pathlib.Path(text).expanduser()
                        filenames = os.listdir(home.as_posix())
                elif text.startswith('~/'):
                    base = pathlib.Path('~/').expanduser()
                    base_length = len(base.as_posix())
                    pattern = text[2:] + '*'
                    filenames = ['~' + f[base_length:]
                                 for f in [p.as_posix() for p in base.glob(pattern)]]
            elif text.startswith('~') and quote is None:
                find_user = text[1:]
                filenames = []
                for username in TabCompleter.usernames():
                    if username.startswith(find_user):
                        filenames.append('~' + username)
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
            # All filenames in current directory
            filenames = [p.relative_to(current_dir).as_posix() for p in current_dir.iterdir()]
        # Append / to dirs
        filenames = [f + '/' if pathlib.Path(f).expanduser().is_dir() else f for f in filenames]
        return filenames

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
    def usernames():
        usernames = []
        with open('/etc/passwd', 'r') as passwds:
            users = passwds.readlines()
        for line in users:
            fields = line.split(':')
            username = fields[0]
            usernames.append(username)
        return usernames

