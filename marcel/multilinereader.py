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

"""input() and the readline module support single-line input. I.e., each time the dude typing on the
keyboard presses Enter, that ends the line of input, which is then added to the history maintained by
readline. It would be nice to type a \\ at the end of the line, and continue typing a command on the next line
(as happens on bash), but that doesn't work.

input() and readline can, however, deal with history items that happen to be multi-line due to embedded \n.
MultiLineReader takes advantage of this. If a line of input is terminated by a continuation string (e.g. \\),
then an additional line of input is requested. This continues until a line is provided that does not end with
the continuation string. MultiLineReader.input reads lines until it detects one not terminated by a continuation
string, and returns those lines concatenated into a string (removing the \\ and \n terminating each non-terminal line).

History items are correctly maintained, replacing multiple continued lines, with the one joined-together line.
When one of these multi-line history items is edited, it shows up to the keyboard dude as it was typed in
originally: multiple lines, with all but the last ending in the continuation string.
"""

import readline

import prompt_toolkit as pt

import marcel.tabcompleter


class MultiLineReader:

    def __init__(self, env, continuation='\\', history_file=None):
        """continuation is the string which is used to denote that an input line is going to be
        continued. It is typically \\, which is the default. If the history file is not specified,
        then multiline items in the history file will not be recalled correctly across process
        boundaries."""
        history_file.touch(0o666)
        self.continuation = continuation
        self.history_file = history_file
        self._fix_history()
        self.tab_completer = marcel.tabcompleter.TabCompleter(env)

    def __getstate__(self):
        assert False, "Don't pickle multilinereader"

    def __setstate__(self, state):
        assert False, "Don't pickle multilinereader"

    def input(self, prompt, continuation_prompt):
        """Get input from the user, similar to the Python input() function. The prompt is printed
        before the first line of input. If the input line ends with the continuation string,
        then additional lines are requested, using the continuation prompt."""
        lines = []
        while True:
            assert prompt is not None and continuation_prompt is not None
            line = pt.prompt(message=pt.ANSI(prompt if len(lines) == 0 else continuation_prompt),
                             complete_while_typing=False,
                             completer=self.tab_completer)
            # The len(lines) > 0 check is needed to fix bug 41.
            if len(line) > 0 or len(lines) > 0:
                history_length = readline.get_current_history_length()
                if history_length > 0:
                    readline.remove_history_item(history_length - 1)
                # If line was recalled from history, then convert to its original multiline form.
                from_history = self._multiline(line)
                if from_history is None:
                    # Wasn't from history
                    lines.append(line)
                else:
                    lines = from_history
                    line = lines[-1]
                if not line.endswith(self.continuation):
                    break
        # Store history as a single line with continuations and line breaks.
        readline.add_history('\n'.join(lines))
        # Return a single string without continuations and line breaks.
        lines[-1] += self.continuation
        return ''.join([line[:-len(self.continuation)] for line in lines])

    def close(self):
        readline.write_history_file(self.history_file)

    def history(self):
        history = []  # Newest first
        n = readline.get_current_history_length()
        i = 1  # readline is 1-based
        while i <= n:
            history.append(readline.get_history_item(i))
            i += 1
        return history

    # A line recalled from history is a single string, constructed by joining together the individual lines
    # with \n. Return the original multi-line form. Return None if the input was not a joined-together line
    # from history.
    def _multiline(self, line):
        lines = []
        join_pattern = self.continuation + '\n'
        position = 0
        start = 0
        while position >= 0:
            position = line.find(join_pattern, start)
            if position >= 0:
                lines.append(line[start:(position + len(self.continuation))])
                start = position + len(join_pattern)  # For next iteration
            else:
                lines.append(line[start:])
        return lines if start > 0 else None

    def _fix_history(self):
        try:
            readline.clear_history()
            readline.read_history_file(self.history_file)
        except FileNotFoundError:
            return
        # Rebuild history items, concatenating lines when indicated by continuation strings.
        history = []
        line = ''
        for i in range(readline.get_current_history_length()):
            line += readline.get_history_item(i + 1)  # 1-based
            if line.endswith(self.continuation):
                line += '\n'
            else:
                history.append(line)
                line = ''
        if len(line) > 0:
            history.append(line)
        # Replace readline's history
        readline.clear_history()
        for item in history:
            readline.add_history(item)
