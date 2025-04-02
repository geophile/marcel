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

"""Controls handling of exceptions and stderr through the setting of handlers.

An C{exception_handler} is a function with these arguments:
    - C{exception}: The exception being handled. In case of a remote exception,
      this exception object is a client-side reconstruction of the server-side exception.
    - C{op}: A op of type C{Op}, or, in case of a remote exception, a op description, obtained by applying C{str()}.
    - C{command_input}: Input to the op that raised the exception.
    - C{thread}: The thread on which the exception occurred.
"""

import sys

import marcel.object.workspace
import marcel.util


# Exception for terminating command. By extending BaseException, this exception
# cannot be caught by "except Exception".
class KillCommandException(BaseException):

    def __init__(self, cause):
        super().__init__(cause)
        self.cause = cause

    def __str__(self):
        return str(self.cause)


class StartupScriptException(KillCommandException):

    def __init__(self, workspace, startup_exception):
        description = 'default workspace' if workspace.is_default() else f'workspace {workspace.name}'
        super().__init__(f'Error during execution of startup script of {description}: {startup_exception}')


# Exception for terminating command for API first().
class StopAfterFirst(BaseException):
    pass


# Used in case of a config file change, or switch to a different workspace.
class ReconfigureException(BaseException):

    def __init__(self, workspace):
        super().__init__()
        self.workspace_to_open = workspace


# Exception thrown to indicate that an op cannot complete for the current input,
# but command execution should continue.
class KillAndResumeException(BaseException):

    def __init__(self, error):
        super().__init__()
        self.error = error

    def __str__(self):
        return str(self.error)


class KillShellException(BaseException):

    def __init__(self, cause):
        super().__init__(cause)


class ExitException(BaseException):
    pass


class ImportException(BaseException):

    def __init__(self, message):
        super().__init__(message)
        self.message = message


# Indicates a marcel command terminating with a ShellString missing a terminating quote.
class MissingQuoteException(KillCommandException):
    def __init__(self, unterminated_string):
        super().__init__(f'Missing quote: {unterminated_string}')
        self.unterminated_string = unterminated_string


def _format_input_for_reporting(command_input, buffer):
    if isinstance(command_input, list):
        buffer.append(str(tuple(command_input)))
    elif isinstance(command_input, tuple):
        buffer.append(str(command_input))
    else:
        buffer.append('(')
        buffer.append(str(command_input))
        buffer.append(')')


def _default_exception_handler(exception, op, command_input, thread=None):
    buffer = []
    if thread:
        buffer.append('on ')
        buffer.append(str(thread))
        buffer.append(': ')
    buffer.append(str(op))
    _format_input_for_reporting(command_input, buffer)
    buffer.append(' ')
    buffer.append(str(exception.__class__))
    buffer.append(': ')
    buffer.append(str(exception))
    print(''.join(buffer), file=sys.stderr)
    marcel.util.print_stack_of_current_exception()


def set_exception_handler(handler):
    """Use C{handler} as the exception handler.
    """
    global exception_handler

    def wrap_provided_exception_handler(exception, op, command_input, thread=None):
        try:
            handler(exception, op, command_input, thread)
        except Exception as e:
            raise KillCommandException(e)
    exception_handler = wrap_provided_exception_handler


def _default_stderr_handler(line, op, command_input, thread=None):
    buffer = []
    if thread:
        buffer.append('on ')
        buffer.append(str(thread))
        buffer.append(': ')
    buffer.append(str(op))
    _format_input_for_reporting(command_input, buffer)
    buffer.append(': ')
    buffer.append(line.rstrip())
    print(''.join(buffer), file=sys.stderr)


def set_stderr_handler(handler):
    """Use C{handler} as the stderr handler.
    """
    def wrap_provided_stderr_handler(line, op, command_input, thread=None):
        try:
            handler(line, op, command_input, thread)
        except Exception as e:
            raise KillCommandException(e)
    global stderr_handler
    stderr_handler = wrap_provided_stderr_handler


exception_handler = _default_exception_handler
stderr_handler = _default_stderr_handler
