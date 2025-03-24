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


class Quote(object):

    SINGLE = "'"
    DOUBLE = '"'
    ALL = SINGLE + DOUBLE

    @staticmethod
    def split_leading_quote(x):
        return (x[0], x[1:]) if len(x) > 0 and x[0] in Quote.ALL else (None, x)

    @staticmethod
    def unquote(x):
        if x:
            if x[0] in Quote.ALL:
                x = x[1:]
            if x[-1] in Quote.ALL:
                x = x[:-1]
        return x


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
        token = None
        self.line = line
        # Parse the text so far, to get information needed for tab completion. It is expected that
        # the text will end early, since we are doing tab completion here. This results in a PrematureEndError
        # which can be ignored. The important point is that the parse will set Parser.op.
        self.parser = marcel.parser.Parser(line, self.env)
        try:
            self.parser.parse()
        except marcel.exception.MissingQuoteException as e:
            token = f'{e.quote}{e.unterminated_string}'
            debug(f'Caught MissingQuoteException: <{token}>')
        except marcel.exception.KillCommandException as e:
            # Parse may have failed because of an unrecognized op, for example. Normal continuation should
            # do the right thing.
            debug(f'Caught KillCommandException: {e}')
        except BaseException as e:
            debug(f'Something went wrong: {e}')
            marcel.util.print_stack_of_current_exception()
        else:
            debug('No exception during parse')
        if token is None:
            token = self.parser.terminal_token_value()
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
        return [candidate.text for candidate in candidates]


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
        unquoted_token = Quote.unquote(token)
        return (UsernameHandler(token) if unquoted_token.startswith('~') and '/' not in unquoted_token else
                AbsDirHandler(token) if unquoted_token.startswith('/') or unquoted_token.startswith('~') else
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
        return Completion(text=(filename[len(self.prefix):] + '/'),
                          display=f'~{filename}')

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
        t = token
        self.quote, token = Quote.split_leading_quote(token)
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
        try:
            dir_contents = (os.listdir(self.expanduser(FilenameHandler.pathlib_path(self.basedir)))
                            if self.basedir else
                            os.listdir())
            return sorted(self.elements_matching_prefix(dir_contents))
        except FileNotFoundError:
            return []

    def expanduser(self, path):
        # Emulate bash behavior for expansion of ~ in a quoted string.
        assert isinstance(path, pathlib.Path), f'({type(path)}) {path}'
        return path.expanduser() if self.quote != Quote.DOUBLE else path

    # Work out the completion's end characters for dir/filename. (The completion contains just filename so far.)
    # - Add a slash if path is a dir.
    # - Add a quote if the token started with a quote, and not a dir
    # - Add a space if not a dir
    def completion_endchars(self, filename):
        path = (FilenameHandler.pathlib_path(filename) if self.basedir is None else
                FilenameHandler.pathlib_path(self.basedir) / filename)
        return ('/' if path.is_dir() else
                (self.quote + ' ') if self.quote else
                ' ')

    @staticmethod
    def pathlib_path(x):
        if type(x) is str:
            path = pathlib.Path(x)
        elif isinstance(x, pathlib.Path):
            path = x
        else:
            assert False, f'({type(x)}) {x}'
        return path

class AbsDirHandler(FilenameHandler):

    def completion(self, filename):
        # text: The completion. What gets appended to what the user typed.
        # display: Appears in list of candidate completions.
        return (Completion(text=filename + self.completion_endchars(filename),
                           display=f'/{filename}')
                if self.basedir == '/' else
                Completion(text=filename[len(self.prefix):] + self.completion_endchars(filename),
                           display=f'{self.basedir}/{filename}'))

class LocalDirHandler(FilenameHandler):

    def completion(self, filename):
        # text: The completion. What gets appended to what the user typed.
        # display: Appears in list of candidate completions.
        return Completion(text=filename[len(self.prefix):] + self.completion_endchars(filename),
                          display=filename)
