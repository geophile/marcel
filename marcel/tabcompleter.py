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

from prompt_toolkit.completion import Completer, Completion, CompleteEvent
from prompt_toolkit.document import Document

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


class TabCompleter(Completer):

    OPS = marcel.op.public
    HELP_TOPICS = list(marcel.doc.topics) + OPS

    def __init__(self, env):
        self.env = env
        self.parser = None
        self.line = None

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
            completer = self.noop
        for c in completer(token):
            yield c

    def __repr__(self):
        return f'TabCompleter({self.line})'

    # Returns the last token encountered by the parse of line
    def parse(self, line):
        self.line = line
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
        def pipeline_syntax(token):
            return (
                # Example: "ls |"
                token == '|' or
                # Example: "ls | args (|"
                token == '(|' or
                # Example: "ls | args (| f:"
                token.endswith(':'))

        debug(f'complete_op: token={token}')
        # We could be in op format but the token is either | or (|....
        if pipeline_syntax(token):
            token = ''
        # Include marcel ops.
        # Include executables only if there are no qualifying ops.
        found_op = False
        for op in TabCompleter.OPS:
            if len(token) == 0 or op.startswith(token):
                yield TabCompleter.string_completion(token, op)
                found_op = True
        if not found_op:
            for exe in TabCompleter.executables():
                if exe.startswith(token):
                    yield TabCompleter.string_completion(token, exe)

    def complete_flag(self, token):
        debug(f'complete_flag: token={token}')
        for flag in sorted(self.parser.flags()):
            if flag.startswith(token):
                yield TabCompleter.string_completion(token, flag)

    # Arg completion assumes we're looking for filenames. (bash does this too.)
    def complete_arg(self, token):
        filename_handler = ArgHandler.select(token)
        for filename in filename_handler.complete_filename():
            yield filename_handler.completion(filename)

    def noop(self, token):
        # There needs to be a yield statement so that this function is recognized as a generator.
        if self is None:
            yield None
        pass

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
    def string_completion(token, completion):
        # text: of the completion; what gets appended.
        # display: appears in list of candidate completions.
        return Completion(text=f'{completion[len(token):]} ',
                          display=completion)

    @staticmethod
    def executables():
        executables = []
        path = os.environ['PATH'].split(':')
        for p in path:
            for f in os.listdir(p):
                if marcel.util.is_executable(f) and f not in executables:
                    executables.append(f)
        return executables

    # For use in testing
    def candidates(self, line):
        document = Document(line)
        event = CompleteEvent(text_inserted=False, completion_requested=True)
        candidates = []
        for candidate in self.get_completions(document, event):
            candidates.append(candidate)
        return [candidate.display_text for candidate in candidates]


class ArgHandler(object):

    def __init__(self, prefix):
        self.prefix = prefix

    def complete_filename(self):
        assert False

    def completion(self, filename):
        assert False

    def elements_matching_prefix(self, candidates):
        return [f for f in candidates if f.startswith(self.prefix)]

    @staticmethod
    def select(token):
        return (UsernameHandler(token) if token.startswith('~') and '/' not in token else
                AbsDirHandler(token) if token.startswith('/') or token.startswith('~') else
                LocalDirHandler(token))

class UsernameHandler(ArgHandler):

    def __init__(self, token):
        super().__init__(prefix=token[1:])  # Everything after ~
        debug(f'{self.__class__.__name__}: prefix={self.prefix}')

    def complete_filename(self):
        return self.elements_matching_prefix(sorted(UsernameHandler.usernames()))

    def completion(self, filename):
        # text: The completion. What gets appended to what the user typed.
        # display: Appears in list of candidate completions.
        text = filename[len(self.prefix):] + '/'
        display = FilenameHandler.add_slash_to_dir(f'~{filename}')
        return Completion(text=text, display=display)

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

class FilenameHandler(ArgHandler):

    def __init__(self, token):
        # basedir and prefix are strings, resulting from splitting the token on the last slash, if there is one.
        # Either may include ~ which would need to be expanded later.
        try:
            last_slash = token.rindex('/')
            self.basedir = token[:last_slash]
            prefix = token[last_slash + 1:]
        except ValueError:
            self.basedir = None
            prefix = token
        super().__init__(prefix=prefix)
        debug(f'{self.__class__.__name__}: basedir={self.basedir}, prefix={self.prefix}')

    def complete_filename(self):
        if self.basedir:
            filenames = self.elements_matching_prefix(sorted(os.listdir(pathlib.Path(self.basedir).expanduser())))
            return [(f'{filename}/' if pathlib.Path(f'{self.basedir}/{filename}').expanduser().is_dir() else filename)
                    for filename in filenames]
        else:
            filenames = self.elements_matching_prefix(sorted(os.listdir()))
            return [FilenameHandler.add_slash_to_dir(filename) for filename in filenames]

    @staticmethod
    def add_slash_to_dir(path):
        if not isinstance(path, pathlib.Path):
            path = pathlib.Path(path)
        return path.as_posix() + '/' if path.expanduser().is_dir() else path.as_posix()

class AbsDirHandler(FilenameHandler):

    def completion(self, filename):
        # text: The completion. What gets appended to what the user typed.
        # display: Appears in list of candidate completions.
        if self.basedir == '/':
            text = filename
            display = f'/{filename}'
        else:
            text = filename[len(self.prefix):]
            display = f'{self.basedir}/{filename}'
        return Completion(text=text, display=display)

class LocalDirHandler(FilenameHandler):

    def completion(self, filename):
        # text: The completion. What gets appended to what the user typed.
        # display: Appears in list of candidate completions.
        text = filename[len(self.prefix):]
        display = filename
        return Completion(text=text, display=display)
