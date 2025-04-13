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
import string

from prompt_toolkit.completion import Completer, Completion, CompleteEvent
from prompt_toolkit.document import Document

import marcel.core
import marcel.doc
import marcel.exception
import marcel.op
import marcel.parser
import marcel.util

DEBUG = False

# See discussion in notes/tab_completion.txt, 3/15/25.
NEEDS_ESCAPE = string.whitespace + '''$!"&'()*:;<>?@[\`{|'''
ESCAPE = '\\'


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
            if len(x) > 0 and x[-1] in Quote.ALL:
                x = x[:-1]
        return x


class TabCompleter(Completer):
    OPS = marcel.op.public

    def __init__(self, env):
        super().__init__()
        self.env = env
        self.parser = None
        self.line = None

    def get_completions(self, document, complete_event):
        token = self.parse(document.text)
        debug(f'get_completions: doc=<{document}> '
              '-----------------------------------------------------------------------------')
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
            token = e.unterminated_string
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
        filename_handler = self.select(token)
        for filename in filename_handler.complete_arg():
            yield filename_handler.completion(filename)

    def noop(self, token):
        # There needs to be a yield statement so that this function is recognized as a generator.
        if self is None:
            yield None
        pass

    def select(self, token):
        unquoted_token = Quote.unquote(token)
        return (HelpTopicHandler(token) if self.help_command() else
                UsernameHandler(token) if unquoted_token.startswith('~') and '/' not in unquoted_token else
                FilenameHandler(token))

    def help_command(self):
        return self.parser.text.strip().startswith('help')

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
            candidates.append(candidate.text)
        debug(f'candidates({line}): {candidates}')
        return candidates


class ArgHandler(object):

    def __init__(self, prefix):
        self.prefix = prefix
        # For purposes of matching filenames to prefix, we need th prefix with escapes resolved.
        self.unescaped_prefix = ArgHandler.resolve_escapes(prefix)

    # Returns a list of the filenames that can complete the last typed token.
    def complete_arg(self):
        assert False

    # Returns a Completion for the given filename (what gets appended,
    # and how it is displayed as a completion option).
    def completion(self, arg):
        assert False

    # For use by subclasses

    def elements_matching_prefix(self, candidates):
        return [f for f in candidates if f.startswith(self.unescaped_prefix)]

    @staticmethod
    def resolve_escapes(x):
        resolved = ''
        i = 0
        while i < len(x):
            c = x[i]
            i += 1
            if c == ESCAPE:
                if i < len(x):
                    c = x[i]
                    i += 1
                    resolved += c
            else:
                resolved += c
        return resolved

class HelpTopicHandler(ArgHandler):

    HELP_TOPICS = sorted(list(marcel.doc.topics) + TabCompleter.OPS)

    def __init__(self, token):
        super().__init__(prefix=token)
        debug(f'{self.__class__.__name__}: prefix={self.prefix}')

    def complete_arg(self):
        return self.elements_matching_prefix(HelpTopicHandler.HELP_TOPICS)

    def completion(self, arg):
        # text: The completion. What gets appended to what the user typed.
        # display: Appears in list of candidate completions.
        return Completion(text=(arg[len(self.prefix):]),
                          display=arg)

    @staticmethod
    def complete_help(text):
        debug(f'complete_help, text = <{text}>')
        candidates = []
        for topic in TabCompleter.HELP_TOPICS:
            if topic.startswith(text):
                candidates.append(topic)
        debug(f'complete_help candidates for <{text}>: {candidates}')
        return candidates


class UsernameHandler(ArgHandler):

    def __init__(self, token):
        super().__init__(prefix=token[1:])  # Everything after ~
        debug(f'{self.__class__.__name__}: prefix={self.prefix}')

    def complete_arg(self):
        return self.elements_matching_prefix(sorted(UsernameHandler.usernames()))

    def completion(self, arg):
        # text: The completion. What gets appended to what the user typed.
        # display: Appears in list of candidate completions.
        return Completion(text=(arg[len(self.unescaped_prefix):] + '/'),
                          display=f'~{arg}')

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
        self.token = token
        self.quote, unquoted_token = Quote.split_leading_quote(token)
        try:
            last_slash = unquoted_token.rindex('/')
            if last_slash == 0:
                # token is of the form /xyz
                self.basedir = '/'
                prefix = unquoted_token[1:]
            else:
                self.basedir = unquoted_token[:last_slash]
                prefix = unquoted_token[last_slash + 1:]
        except ValueError:
            self.basedir = None
            prefix = unquoted_token
        super().__init__(prefix=prefix)
        self.last_char_replacement_text = None  # The last character of the token may need to be escaped.
        self.cursor_adjustment = 0
        self.compute_token_escaping(unquoted_token)
        debug(f'{self.__class__.__name__}: basedir=<{self.basedir}>, prefix=<{self.prefix}>')

    def complete_arg(self):
        try:
            basedir = marcel.util.unescape(self.basedir)
            dir_contents = (os.listdir(self.expanduser(FilenameHandler.pathlib_path(basedir)))
                            if basedir else
                            os.listdir())
            return sorted(self.elements_matching_prefix(dir_contents))
        except FileNotFoundError:
            return []

    def completion(self, arg):
        # text: The completion. What gets appended to what the user typed.
        # display: Appears in list of candidate completions.
        prefix = arg[:len(self.unescaped_prefix)]
        suffix = arg[len(self.unescaped_prefix):]
        return Completion(text=self.completion_text(prefix, suffix),
                          display=f'{arg}',
                          start_position=self.cursor_adjustment)
    # The completion text is passed in as:
    #   - prefix (stuff typed already), and
    #   - suffix (stuff ot be appended).
    # Escape NEEDS_ESCAPE characters in the suffix if the filename is not quoted.
    # Also, check the last prefix character and escape that if needs to be escaped and isn't already
    # escaped.
    # Also work out what needs to be appended:
    #     - Add a slash if path is a dir.
    #     - Add a quote if the token started with a quote, and not a dir
    #     - Add a space if not a dir
    def completion_text(self, prefix, suffix):
        if self.quote is None:
            completion_text = ''
            # Add escapes
            # - Handle escaping of the last typed character
            if self.last_char_replacement_text is not None:
                completion_text = self.last_char_replacement_text
                self.cursor_adjustment = -1
            # - Fix the suffix
            for c in suffix:
                if c in NEEDS_ESCAPE:
                    completion_text += ESCAPE
                completion_text += c
        else:
            completion_text = suffix
        filename = prefix + suffix
        path = (FilenameHandler.pathlib_path(filename) if self.basedir is None else
                FilenameHandler.pathlib_path(self.basedir) / filename)
        path = path.expanduser()
        completion_text += ('/' if path.is_dir() else
                            (self.quote + ' ') if self.quote else
                            ' ')
        debug(f'completion_text(<{prefix}>, <{suffix}>): quote=<{self.quote}> -> <{completion_text}>')
        return completion_text


    def expanduser(self, path):
        # Emulate bash behavior for expansion of ~ in a quoted string.
        assert isinstance(path, pathlib.Path), f'({type(path)}) {path}'
        return path.expanduser() if self.quote != Quote.DOUBLE else path

    def compute_token_escaping(self, unquoted_token):
        if len(unquoted_token) > 0:
            c = unquoted_token[-1]
            if c in NEEDS_ESCAPE:
                d = None if len(unquoted_token) == 1 else unquoted_token[-2]
                if d != ESCAPE:
                    self.last_char_replacement_text = f'{ESCAPE}{c}'
    @staticmethod
    def pathlib_path(x):
        if isinstance(x, str):
            path = pathlib.Path(x)
        elif isinstance(x, pathlib.Path):
            path = x
        else:
            assert False, f'({type(x)}) {x}'
        return path
