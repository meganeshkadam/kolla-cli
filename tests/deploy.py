# Copyright(c) 2015, Oracle and/or its affiliates.  All Rights Reserved.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#
from common import KollaCliTest

from kollacli.ansible.inventory import Inventory
from kollacli.ansible.inventory import SERVICES

import json
import os
import tarfile
import unittest


class TestFunctional(KollaCliTest):

    def test_json_generator(self):
        self.run_cli_cmd('setdeploy local')

        host1 = 'host_test1'
        self.run_cli_cmd('host add %s' % host1)

        inventory = Inventory.load()

        path = inventory.create_json_gen_file()
        (retval, msg) = self.run_command(path)
        os.remove(path)
        self.assertEqual(0, retval, 'json generator command failed: %s' % msg)

        self.assertNotEqual('', msg, 'json generator returned no data: %s'
                            % msg)

        self.assertIn(host1, msg, '%s not in json_gen output: %s'
                      % (host1, msg))

        for service, subservices in SERVICES.items():
            self.assertIn(service, msg, '%s not in json_gen output: %s'
                          % (service, msg))
            for subservice in subservices:
                self.assertIn(subservice, msg, '%s not in json_gen output: %s'
                              % (subservice, msg))

        # verify that json output is valid. This will throw if invalid json
        try:
            json.loads(msg)
        except Exception:
            self.assertTrue(False, 'invalid json: %s' % msg)
        remote_msg = '"ansible_ssh_user": "kolla"'
        local_msg = '"ansible_connection": "local"'

        # verify that setdeploy local worked:
        self.assertIn(local_msg, msg, '%s not in local json_gen output: %s'
                      % (local_msg, msg))
        self.assertNotIn(remote_msg, msg, '%s in local json_gen output: %s'
                         % (remote_msg, msg))

        # verify that setdeploy remote worked:
        self.run_cli_cmd('setdeploy remote')
        inventory = Inventory.load()
        path = inventory.create_json_gen_file()
        (retval, msg) = self.run_command(path)
        os.remove(path)
        self.assertEqual(0, retval, 'json generator command failed: %s' % msg)

        self.assertIn(remote_msg, msg, '%s not in remote json_gen output: %s'
                      % (remote_msg, msg))
        self.assertNotIn(local_msg, msg, '%s in remote json_gen output: %s'
                         % (local_msg, msg))

    def test_json_filtering(self):

        hosts = ['host_test1', 'host_test2', 'host_test3']
        groups = ['control', 'network', 'storage']

        for host in hosts:
            self.run_cli_cmd('host add %s' % host)
            for group in groups:
                self.run_cli_cmd('group addhost %s %s' % (group, host))

        inventory = Inventory.load()

        # filter by host- include all hosts
        inv_filter = {'deploy_hosts': hosts}
        path = inventory.create_json_gen_file(inv_filter)
        self.log.info('run command: %s' % path)
        (retval, msg) = self.run_command(path)
        os.remove(path)
        self.assertEqual(0, retval, 'json generator command failed: %s' % msg)

        self.check_json(msg, groups, hosts, groups, hosts)

        # filter by host- to first host
        included_host = hosts[0]
        inv_filter = {'deploy_hosts': [included_host]}
        path = inventory.create_json_gen_file(inv_filter)
        self.log.info('run command: %s' % path)
        (retval, msg) = self.run_command(path)
        os.remove(path)
        self.assertEqual(0, retval, 'json generator command failed: %s' % msg)
        self.check_json(msg, groups, hosts, groups, [included_host])

        # filter by group- include all groups
        inv_filter = {'deploy_groups': groups}
        path = inventory.create_json_gen_file(inv_filter)
        self.log.info('run command: %s' % path)
        (retval, msg) = self.run_command(path)
        os.remove(path)
        self.assertEqual(0, retval, 'json generator command failed: %s' % msg)
        self.check_json(msg, groups, hosts, groups, hosts)

        # filter by group- to first group
        included_group = groups[0]
        inv_filter = {'deploy_groups': [included_group]}
        path = inventory.create_json_gen_file(inv_filter)
        self.log.info('run command: %s' % path)
        (retval, msg) = self.run_command(path)
        os.remove(path)
        self.assertEqual(0, retval, 'json generator command failed: %s' % msg)
        self.check_json(msg, groups, hosts, [included_group], hosts)

    def test_deploy(self):
        # test will start with no hosts in the inventory
        # deploy will throw an exception if it fails
        self.run_cli_cmd('deploy')
        self.run_cli_cmd('deploy --serial')
        self.run_cli_cmd('deploy --groups=control')

    def test_dump(self):
        check_files = [
            'var/log/kolla/kolla.log',
            'kolla/etc/globals.yml',
            'kolla/etc/config/nova/nova-api.conf',
            'kolla/etc/kollacli/ansible/inventory.json',
            'kolla/share/ansible/site.yml',
            'kolla/share/docs/ansible-deployment.rst',
        ]
        # dump success output is:
        # dump successful to /tmp/kollacli_dump_Umxu6d.tgz
        dump_path = None
        try:
            msg = self.run_cli_cmd('dump')
            self.assertIn('/', msg, 'path not found in dump output: %s' % msg)

            dump_path = '/' + msg.strip().split('/', 1)[1]
            is_file = os.path.isfile(dump_path)
            self.assertTrue(is_file,
                            'dump file not found at %s' % dump_path)

            file_paths = []
            with tarfile.open(dump_path, 'r') as tar:
                file_paths = tar.getnames()

            for check_file in check_files:
                self.assertIn(check_file, file_paths,
                              'dump: check file: %s, not in files:\n%s'
                              % (check_file, file_paths))
        except Exception as e:
            raise e
        finally:
            if dump_path and os.path.exists(dump_path):
                os.remove(dump_path)

    def check_json(self, msg, groups, hosts, included_groups, included_hosts):
        err_msg = ('included groups: %s\n' % included_groups +
                   'included hosts: %s\n' % included_hosts)
        inv_dict = json.loads(msg)
        for group in groups:
            group_hosts = inv_dict[group]['hosts']
            for host in hosts:
                if group in included_groups and host in included_hosts:
                    self.assertIn(host, group_hosts, err_msg +
                                  '%s not in %s' % (host, group_hosts))
                else:
                    self.assertNotIn(host, group_hosts, err_msg +
                                     '%s still in %s' % (host, group_hosts))


if __name__ == '__main__':
    unittest.main()
