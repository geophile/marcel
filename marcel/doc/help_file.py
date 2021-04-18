# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or at your
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
A {i:File} encapsulates a path,
e.g. {n:/home/jao/git/marcel/setup.py}.  Marcel's {n:ls} command
generates a stream of {n:File}s.  {n:File} provides a large set of
properties and functions for file path manipulations, and for
accessing file metadata and content.

{b:Path functions}

The standard Python module {n:pathlib} provides an extensive interface
operating on paths. While {n:File} is not a subclass of
{n:pathlib.Path}, it does offer the same functions. So, for example,
you can use {n:pathlib}'s {r:parts} property to break down a {n:File}'s path
into its components:

{L,wrap=F}ls | map (file: file.parts)

{b:File metadata}

Since {n:pathlib.Path} does offer a {n:stat()} method, you can use it
to obtain file metadata. For example, to print name of each listed file,
along with its uid and gid:

{L,wrap=F}ls | map (file: (file, file.stat())) | map (file, stat: (file, stat[4], stat[5]))

{r:stat()} returns an {n:os.stat_result} object, which
has the uid and gid in positions 4 and 5.

{n:File} also has convenience function so that you don't have to invoke {r:stat()} directly
and then figure out how to obtain the metadata of interest from an {n:os.stat_result} object.
So the same result can be obtained as follows:

{L,wrap=F}ls | map (file: (file, file.uid, file.gid))

The following file metadata properties are available on {n:File}s:

{L}- mode
{L}- inode
{L}- device
{L}- links
{L}- uid
{L}- gid
{L}- size
{L}- atime
{L}- ctime
{L}- mtime

{r:atime}, {r:ctime}, and {r:mtime} return seconds since the epoch
(January 1, 1970). These can be used with the functions {n:now}, {n:hours},
and {n:minutes} to select files based on these times. For example, this
command finds files under {n:/etc} that have been modified in the past day:

{L,wrap=F}ls -fr /etc | select (f: now() - f.mtime <= days(1))

Run {n:help namespace} for more information on builtin functions.

{b:File content}

{n:File} has a {n:read} function, to read the contents of a file as a
single string. The function {n:readlines} returns a list of lines,
in which trailing newline characters are removed.  '''
