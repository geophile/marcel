# input() and the readline module support single-line input. I.e., each time the keyboard dude presses
# return, that ends the line of input, and adds that line to history. Typing \ and \n at the end of the
# line doesn't help.
#
# input() and readline can, however, deal with history items that happen to be multi-line due to embedded \n.
# MultiLineInput takes advantage of this. If a line of input is terminated by a continuation string (e.g. \),
# then an additional line of input is requested. This continues until a line is provided that does not end with
# the continuation string.
#
# History is maintained to replace the individual lines of input by a join of those lines (with \n added between
# lines. When a line of history is recalled, the multi-line form is restored.

import readline


class MultiLineInput:

    def __init__(self, continuation):
        self.continuation = continuation

    def input(self, prompt, continuation_prompt):
        lines = []
        while True:
            line = input(prompt if len(lines) == 0 else continuation_prompt)
            if len(line) > 0:
                readline.remove_history_item(readline.get_current_history_length() - 1)
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
