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
Marcel provides types representing 
hosts, processes, and files and directories. 

{b:Rendering objects}

Objects sometimes need to be described textually. For example, the
{n:ls} command produces a stream of {n:File} objects.
Every pipelines has an implicit {n:out} operator at the end,
and when {n:out} receives a {n:File}, it uses one of two {i:rendering}
functions:

{L}- {n:render_full()} is called when the object is transmitted to {n:out} in
a 1-tuple, i.e., it is the only thing being printed.

{L}- {n:render_compact()} is called when the object is part of an
n-tuple, n > 1.

For example, the command {n:ls /bin/less*} produces this output, by calling {n:File.render_full()}

{L,wrap=F,indent=4:4}
-rwxr-xr-f   root     root           170760   2018 May 03 10:16:28   less
-rwxr-xr-f   root     root            10256   2018 May 03 10:16:28   lessecho
lrwxrwxrwx   root     root                8   2018 May 03 10:16:28   lessfile -> lesspipe
-rwxr-xr-f   root     root            19856   2018 May 03 10:16:28   lesskey
-rwxr-xr-f   root     root             8564   2018 May 03 10:16:28   lesspipe

But if the tuple carrying a {n:File} to {n:out} has other values too, then
{n:File.render_compact()} is used. So the command {n:ls /bin/less* | map (f: (f, f.size)}
produces this output:

{L,wrap=F,indent=4:4}
('less', 170760)
('lessecho', 10256)
('lessfile', 8)
('lesskey', 19856)
('lesspipe', 8564)


{b:Object types}

Use the {n:help} command to get more information on the following kinds of objects:

{L}- {n:file}
{L}- {n:process}
{L}- {n:history_record}
'''
