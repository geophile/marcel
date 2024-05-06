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

import marcel.exception
import marcel.locations
import marcel.version
import marcel.migration.migration024

PREMIGRATION = '0.0'


def installed_version(locations):
    version_file_path = locations.version_file_path()
    if version_file_path.exists():
        with open(version_file_path) as version_file:
            installed_version = version_file.readline().strip()
    else:
        installed_version = PREMIGRATION
    return installed_version


def migrate():
    def create_marcel_dirs():
        # These calls create the directories if they don't exist
        locations.config_base_path()
        locations.data_base_path()

    def create_version_file():
        version_file_path = locations.version_file_path()
        with open(version_file_path, 'w') as version_file:
            version_file.write(marcel.version.VERSION)
        version_file_path.chmod(0o400)

    def update_version_file():
        # Write current version number to VERSION file, which should already exist.
        if iv < marcel.version.VERSION:
            version_file_path = locations.version_file_path()
            version_file_path.chmod(0o600)
            with open(version_file_path, 'w') as version_file:
                version_file.write(marcel.version.VERSION)
            version_file_path.chmod(0o400)

    locations = marcel.locations.Locations()
    if locations.fresh_install():
        create_marcel_dirs()
        create_version_file()
    else:
        iv = installed_version(locations)
        if iv < '0.24':
            marcel.migration.migration024.migrate(locations)
        update_version_file()
    assert installed_version(locations) == marcel.version.VERSION

