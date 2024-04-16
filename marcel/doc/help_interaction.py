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

HELP = '''
You interact with marcel in the same way as other shells. You run
commands, you can recall the job history, you can edit and rerun
commands from the history, and you can run jobs in the foreground or
background.

{b:Running commands}

Marcel can accept a command when the prompt is present. Otherwise, a command is
running. You can kill a foreground command at any time by pressing Ctrl-C.

In general, the traditional keyboard interactions for a Linux shell can be used,
e.g.

{L,indent=4:6}- Left and right arrows for navigating within a command.
{L,indent=4:6}- Up and down arrows for traversing command history.
{L,indent=4:6}- Ctrl-A to go to the beginning of the current command
{L,indent=4:6}- Ctrl-E to go to the end of the current command.
{L,indent=4:6}- Ctrl-K to delete everything to the end of the current command.
{L,indent=4:6}- Ctrl-U to delete everything to the beginning of the current command.
{L,indent=4:6}- Ctrl-W to delete the preceding word.
{L,indent=4:6}- Ctrl-R to search the command history.

For a multi-line command, type a \\\\ and then hit return. You will then see a
{i:continuation prompt}, following each line ending with a \\\\. (Run {n:help prompt} 
for more information on prompts.)

All text following a {n:#} on the command line is ignored, i.e., the text
following the {n:#} is considered to be a comment. This is useful in scripts
loaded on startup (run {n:help startup} for more information); and to stash a long
command in history for later use.


{b:Command history}

A history of commands entered to marcel is maintained. You can examine this history
by running the {n:history} command. Each command has a numeric id preceding it.
The history is printed in chronological order, and larger numeric ids correspond
to more recent commands. Example:

{p,wrap=F,indent=4}
M jao@cheese:~$ history
...
  418:  cd ../..
  419:  git status
  420:  git diff > /tmp/marcel.diff
  421:  git commit -a
 
{b:Editing commands}

You can edit previous command using your editor of choice, configured using the
{n:EDITOR} environment variable (defined in either marcel's environment,
or inherited from parent process).

To edit the previous command run the {n:edit} command.
To edit a different command run the {n:edit} command, and provide the command number
from the command history.

Once you have saved the edited file, you will see a prompt and the modified command.
You can then edit the command further on the command line, or hit enter to execute it.

{b:Foreground and background}

Marcel will wait for a command to complete execution before providing
another prompt. I.e., the command runs in the {i:foreground}. You can suspend
this command by typing Ctrl-Z. The job then goes into the {i:background}, in a suspended
state. You are then provided with a prompt, allowing you to initiate another command
(which will run in the foreground).

The {n:jobs} command will list all current jobs. (Those will all be in the background
since the {n:jobs} command itself was running in the foreground when it produced
the list of commands.)

To run a suspended job in the background, use the {n:bg} command, identifying the
job by its job number. The {n:fg} command will run a suspended job, placing it in
the foreground.
'''
