# Copyright(c) 2015, Oracle and/or its affiliates.  All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""Command-line interface to Kolla"""
import logging
import os
import sys

from cliff.app import App
from cliff.commandmanager import CommandManager

from kollacli.ansible.inventory import INVENTORY_PATH
from kollacli.exceptions import CommandError
from kollacli.utils import get_kolla_log_dir
from kollacli.utils import get_kolla_log_file_size
from kollacli.utils import get_kollacli_etc


class KollaCli(App):
    log = logging.getLogger(__name__)

    def __init__(self):
        super(KollaCli, self).__init__(
            description='Command-Line Client for OpenStack Kolla',
            version='0.1',
            command_manager=CommandManager('kolla.cli'),
            )

        # check that current user is in the kolla group
        inventory_path = os.path.join(get_kollacli_etc(),
                                      INVENTORY_PATH)
        errString = 'Required file %s does not exist.\n' + \
                    'Please re-install the kollacli to recreate the file.'
        if os.path.isfile(inventory_path) is False:
            raise CommandError(errString % inventory_path)

        inventory_file = None
        try:
            inventory_file = open(inventory_path, 'r+')
        except Exception:
            raise CommandError('Permission denied to run the kollacli.' +
                               '\nPlease add user to the kolla group and ' +
                               'then log out and back in.')
        finally:
            if inventory_file and inventory_file.close is False:
                inventory_file.close()

        self.rotating_log_dir = get_kolla_log_dir()
        self.max_bytes = get_kolla_log_file_size()
        self.backup_count = 4

        self.dump_stack_trace = False

        self.add_rotational_log()

    def clean_up(self, cmd, result, err):
        self.log.debug('clean_up %s', cmd.__class__.__name__)
        if err:
            self.log.debug('error: %s', err)

    def add_rotational_log(self):
        root_logger = logging.getLogger('')
        rotate_handler = logging.handlers.RotatingFileHandler(
            os.path.join(self.rotating_log_dir, 'kolla.log'),
            maxBytes=self.max_bytes,
            backupCount=self.backup_count)
        formatter = logging.Formatter(self.LOG_FILE_MESSAGE_FORMAT)
        rotate_handler.setFormatter(formatter)
        rotate_handler.setLevel(logging.INFO)
        root_logger.addHandler(rotate_handler)


def main(argv=sys.argv[1:]):
    shell = KollaCli()
    return shell.run(argv)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
