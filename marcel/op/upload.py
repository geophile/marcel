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

import pathlib

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.main
import marcel.object.file
import marcel.opmodule
import marcel.op.bash
import marcel.op.fork

File = marcel.object.file.File

HELP = '''
{L,wrap=F}upload CLUSTER DIR FILENAME ...

{L,indent=4:28}{r:CLUSTER}                 The cluster to which files will be uploaded.

{L,indent=4:28}{r:DIR}                     The directory on each cluster node to receive uploaded files.

{L,indent=4:28}{r:FILENAME}                A filename or glob pattern.

Copies local files to the indicated directory on each node of a cluster. The output stream is empty.

The files to be copied are specified by one or more FILENAMEs. Each
FILENAME is a file name or a glob pattern.

CLUSTER must be configured for marcel, (run "help cluster" for
information on configuring clusters).

DIR must be an absolute path, corresponding to a pre-exising directory
on each node of the CLUSTER. The user configured for cluster access
must have permission to write to the directory.
'''


def upload(env, cluster, dir, *paths):
    return Upload(env), [cluster, dir, paths]


class UploadArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('upload', env)
        self.add_anon('cluster', convert=self.cluster)
        self.add_anon('dir', convert=self.check_str_or_file, target='dir_arg')
        self.add_anon_list('filenames', convert=self.check_str_or_file, target='filenames_arg')
        self.validate()


class Upload(marcel.core.Op):
    SCP_COMMAND = 'scp -Cpqr -i {identity} {sources} {user}@{host}:{dest}'

    def __init__(self, env):
        super().__init__(env)
        self.cluster = None
        self.dir_arg = None
        self.dir = None
        self.filenames_arg = None
        self.filenames = None

    def __repr__(self):
        return f'upload({self.cluster}:{self.dir_arg} {self.filenames_arg})'

    def setup(self):
        self.dir = self.eval_function('dir_arg',
                                      str,
                                      pathlib.Path, pathlib.PosixPath, File)
        print(f'dir: {self.dir}')
        self.filenames = self.eval_function('filenames_arg',
                                            str,
                                            pathlib.Path, pathlib.PosixPath, File)
        print(f'filenames: {self.filenames}')
        if len(self.filenames) == 0:
            raise marcel.exception.KillCommandException(f'No qualifying paths, (possibly due to permission errors):'
                                                        f' {self.filenames}')

    def run(self):
        host_pipeline = marcel.core.Pipeline()
        host_pipeline.set_error_handler(self.owner.error_handler)
        host_pipeline.append(marcel.opmodule.create_op(self.env(), 'bash', '(scp_command)'))
        host_pipeline.set_parameters(['scp_command'])
        print(f'host_pipeline: {host_pipeline}')
        pipeline = marcel.core.Pipeline()
        pipeline.set_error_handler(self.owner.error_handler)
        sources = ' '.join(self.filenames)
        scp_commands = [Upload.scp_command(identity=self.cluster.identity,
                                           sources=sources,
                                           user=self.cluster.user,
                                           host=host,
                                           dest=self.dir)
                        for host in self.cluster]
        print(f'scp_commands: {scp_commands}')
        pipeline.append(marcel.opmodule.create_op(self.env(), 'fork', scp_commands, host_pipeline))
        print(f'pipeline: {pipeline}')
        marcel.core.Command(self.env(), None, pipeline).execute()

    @staticmethod
    def scp_command(identity, sources, user, host, dest):
        return Upload.SCP_COMMAND.format(identity=identity,
                                         sources=sources,
                                         user=user,
                                         host=host,
                                         dest=dest)
