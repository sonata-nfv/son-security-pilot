"""
Copyright (c) 2015 SONATA-NFV
ALL RIGHTS RESERVED.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Neither the name of the SONATA-NFV [, ANY ADDITIONAL AFFILIATION]
nor the names of its contributors may be used to endorse or promote
products derived from this software without specific prior written
permission.

This work has been performed in the framework of the SONATA project,
funded by the European Commission under Grant number 671517 through
the Horizon 2020 and 5G-PPP programmes. The authors would like to
acknowledge the contributions of their colleagues of the SONATA
partner consortium (www.sonata-nfv.eu).
"""

import logging
import yaml
import os
import sys
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager
from ansible.inventory import Inventory
from ansible.executor.playbook_executor import PlaybookExecutor
from sonsmbase.smbase import sonSMbase

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("fsm-vpn-config-1")
LOG.setLevel(logging.DEBUG)
logging.getLogger("son-mano-base:messaging").setLevel(logging.INFO)


class VPNConfigurationFSM(sonSMbase):

    def __init__(self):

        self.specific_manager_type = 'fsm'
        self.service_name = 'psa-service'  # TODO: match nsd name
        self.function_name = 'vpn-vnf'
        self.specific_manager_name = 'vpn-config'
        self.id_number = '1'
        self.version = 'v0.1'
        self.description = "FSM for configuring the VPN VNF"

        self.amqp_topic = ('son.' + self.specific_manager_name +
                           self.id_number + self.version)

        super(self.__class__, self).__init__(
            specific_manager_type=self.specific_manager_type,
            service_name=self.service_name,
            function_name=self.function_name,
            specific_manager_name=self.specific_manager_name,
            id_number=self.id_number,
            version=self.version,
            description=self.description)

    def on_registration_ok(self):

        LOG.debug("Received registration ok event.")

        # send the status to the SMR (not necessary)
        self.manoconn.publish(topic='specific.manager.registry.ssm.status',
                              message=yaml.dump(
                                {'name': self.specific_manager_id,
                                 'status': 'Registration is done, '
                                 'initialising the configuration...'}))

        # subscribes to related topic (could be any other topic)
        self.manoconn.subscribe(self.on_configuration,
                                topic=self.amqp_topic)

    def on_configuration(self, ch, method, props, response):

        if props.app_id != self.specific_manager_id:
            LOG.info('Start retrieving the IP address ...')
            response = yaml.load(str(response))
            list = response['VNFR']
            mgmt_ip = None
            vm_image = 'http://files.sonata-nfv.eu/son-psa-pilot/vpn-vnf/' \
                       'sonata-vpn.qcow2'

            for x in range(len(list)):
                if (response['VNFR'][x]['virtual_deployment_units']
                        [0]['vm_image']) == vm_image:
                    mgmt_ip = (response['VNFR'][x]['virtual_deployment_units']
                               [0]['vnfc_instance'][0]['connection_points'][0]
                               ['type']['address'])

            if not mgmt_ip:
                LOG.error("Couldn't obtain IP address from VNFR")
                return

            # send the status to the SMR (not necessary)
            self.manoconn.publish(
                topic='specific.manager.registry.ssm.status',
                message=yaml.dump(
                    {'name': self.specific_manager_id,
                     'status': "IP address:'{0}'".format(host_ip)}))

            LOG.info("IP address:'{0}'".format(mgmt_ip))

            self.manoconn.notify(topic=self.amqp_topic,
                                 msg=yaml.dump(
                                     {'name': self.specific_manager_id,
                                      'IP': mgmt_ip}))

            # configure vm using ansible playbook
            variable_manager = VariableManager()
            loader = DataLoader()

            inventory = Inventory(loader=loader,
                                  variable_manager=variable_manager)

            playbook_path = 'fsm/vpn-config/ansible/site.yml'

            if not os.path.exists(playbook_path):
                LOG.error('The playbook does not exist')
                return

            Options = namedtuple('Options',
                                 ['listtags', 'listtasks', 'listhosts',
                                  'syntax', 'connection', 'module_path',
                                  'forks', 'remote_user', 'private_key_file',
                                  'ssh_common_args', 'ssh_extra_args',
                                  'sftp_extra_args', 'scp_extra_args',
                                  'become', 'become_method', 'become_user',
                                  'verbosity', 'check'])
            options = Options(listtags=False, listtasks=False, listhosts=False,
                              syntax=False, connection='ssh', module_path=None,
                              forks=100, remote_user='slotlocker',
                              private_key_file=None, ssh_common_args=None,
                              ssh_extra_args=None, sftp_extra_args=None,
                              scp_extra_args=None, become=True,
                              become_method=None, become_user='root',
                              verbosity=None, check=False)

            variable_manager.extra_vars = {'hosts': mgmt_ip}

            passwords = {}

            pbex = PlaybookExecutor(playbooks=[playbook_path],
                                    inventory=inventory,
                                    variable_manager=variable_manager,
                                    loader=loader, options=options,
                                    passwords=passwords)

            results = pbex.run()

            return

def main():
    VPNConfigurationFSM()

if __name__ == '__main__':
    main()
