"""C{edit}

Open the most recently entered command in the text editor specified by the EDITOR environment variable.
On exiting the editor, the command will be executed.
"""

import os
import readline
import subprocess
import tempfile

import marcel.core
import marcel.exception
import marcel.main


def edit():
    return Edit()


class EditArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('edit')


class Edit(marcel.core.Op):

    argparser = EditArgParser()

    def __init__(self):
        super().__init__()
        self.editor = None
        self.tmp_file = None

    def __repr__(self):
        return 'edit()'

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup_1(self):
        self.editor = os.getenv('EDITOR')
        if self.editor is None:
            raise marcel.exception.KillCommandException('Specify editor in the EDITOR environment variable')
        _, self.tmp_file = tempfile.mkstemp(text=True)

    def receive(self, _):
        # Remove the edit command from history
        readline.remove_history_item(readline.get_current_history_length() - 1)
        # The last command (the one before edit) is the one of interest.
        command = readline.get_history_item(readline.get_current_history_length())  # 1-based
        with open(self.tmp_file, 'w') as output:
            output.write(command)
        edit_command = f'{self.editor} {self.tmp_file}'
        process = subprocess.Popen(edit_command,
                                   shell=True,
                                   executable='/bin/bash',
                                   universal_newlines=True)
        process.wait()
        with open(self.tmp_file, 'r') as input:
            command_lines = input.readlines()
        self.global_state().edited_command = ''.join(command_lines)
        os.remove(self.tmp_file)

    # Op

    def arg_parser(self):
        return Edit.argparser

    def must_be_first_in_pipeline(self):
        return True
