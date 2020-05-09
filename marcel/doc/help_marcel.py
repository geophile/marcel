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
To learn more about a topic, run the command:

    help TOPIC

Available topics:

{b:Top-level help:}

{p,wrap=F}
    - {n:marcel}

(Or just run {n:help} with no topic.)

{b:Overview:}

{p,wrap=F}
    - {n:configuration}: How to configure the prompt, color scheme, remote access.
    - {n:overview}: The main concepts of marcel. How it differs from other shells.
    - {n:interaction}: Interacting with marcel.
    - {n:command}: Marcel operators, Linux executables.
    - {n:function}: Several operators rely on Python functions.
    - {n:pipeline}: Structuring commands into sequences, using pipes.
    - {n:object}: The objects you work with. 

{b:Objects:}

{p,wrap=F}
    - {n:file}
    - {n:process}

{b:Operators:}

{p,wrap=F}
    - {n:bash}        - {n:bg}          - {n:cd}
    - {n:dirs}        - {n:edit}        - {n:expand}
    - {n:fg}          - {n:gen}         - {n:head}
    - {n:help}        - {n:jobs}        - {n:ls}
    - {n:map}         - {n:out}         - {n:popd}
    - {n:ps}          - {n:pushd}       - {n:pwd}
    - {n:red}         - {n:reverse}     - {n:select}
    - {n:sort}        - {n:squish}      - {n:sudo}
    - {n:tail}        - {n:timer}       - {n:unique}
    - {n:version}     - {n:window}
'''
