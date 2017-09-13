#!/usr/bin/env python3

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
import time
import tempfile
import json
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager
from ansible.inventory import Inventory
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.cli.playbook import PlaybookCLI
from sonsmbase.smbase import sonSMbase
from ansible.plugins.callback import CallbackBase
from ansible.plugins.callback.default import CallbackModule
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.playbook import Playbook
from ansible.playbook.play import Play

#logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)
#LOG.setLevel(logging.DEBUG)
#logging.getLogger("son-mano-base:messaging").setLevel(logging.INFO)


class SampleCallback(CallbackBase):
    def v2_runner_on_ok(self, result, **kwargs):
        """Print a json representation of the result
        This method could store the result in an instance attribute for retrieval later
        """
        host = result._host
        print(json.dumps({host.name: result._result}, indent=4))


class sonfsmvprxsquidconfiguration1(sonSMbase):

    def __init__(self):

        """
        :param specific_manager_type: specifies the type of specific manager that could be either fsm or ssm.
        :param service_name: the name of the service that this specific manager belongs to.
        :param function_name: the name of the function that this specific manager belongs to, will be null in SSM case
        :param specific_manager_name: the actual name of specific manager (e.g., scaling, placement)
        :param id_number: the specific manager id number which is used to distinguish between multiple SSM/FSM
        that are created for the same objective (e.g., scaling with algorithm 1 and 2)
        :param version: version
        :param description: description
        """
        self.specific_manager_type = 'fsm'
        self.service_name = 'vprx'
        self.function_name = 'squid'
        self.specific_manager_name = 'configuration'
        self.id_number = '1'
        self.version = 'v1'
        self.description = "FSM configuring a vProxy (Squid based with local cache and authentication)"
        self.vnfs = []
        self.amqp_topic = ('son.' + self.specific_manager_name + '.' + self.id_number + '.' + self.version)
        #self.amqp_topic = 'son.configuration'

        LOG.debug("super __init__ with amqp_topic=%s", self.amqp_topic)
        super(self.__class__, self).__init__(specific_manager_type=self.specific_manager_type,
                                             service_name=self.service_name,
                                             function_name=self.function_name,
                                             specific_manager_name=self.specific_manager_name,
                                             id_number=self.id_number,
                                             version=self.version,
                                             description=self.description)

    def on_registration_ok(self):
        LOG.debug("Received registration ok event.")
        # # send the status to the SMR (not necessary)
        # self.manoconn.publish(topic='specific.manager.registry.ssm.status', message=yaml.dump(
        #                           {'name': self.specific_manager_id, 'status': 'Registration is done, '
        #                                                       'initialising the configuration...'}))

        # subscribes to related topic (could be any other topic)
        LOG.debug("Subscribing on the on_configuration event in the '{}' topic".format(self.amqp_topic))
        self.manoconn.subscribe(self.on_configuration, topic=self.amqp_topic)

    def on_configuration(self, ch, method, props, response):
        LOG.debug("Received on_configuration event.")
        if props.app_id != self.specific_manager_id:
            LOG.info('Start retrieving the IP address ...')
            response = yaml.load(str(response))
            list = response['VNFR']
            self.is_in_sonemulator = response['_in_sonemulator']
            host_ip = None

            for x in list:
                LOG.debug("x=%s, %s", type(x), x)
                tmp_vm_image = x['virtual_deployment_units'][0]['vm_image']
                #if tmp_vm_image in ['squid', 'squid:latest', 'sonata-psa/squid', 'sonata-psa/squid:latest']:
                tmp_base = x['virtual_deployment_units'][0]['vnfc_instance'][0]
                host_ip = tmp_base['connection_points'][0]['interface']['address']
                if not host_ip:
                    LOG.error("Couldn't get IP address from VNFR with image %s", tmp_vm_image)
                    continue
                tmp_res = {'ip': host_ip, 'image': tmp_vm_image, 'id': tmp_base['vc_id']}
                LOG.info('Result=%s for image %s', tmp_res, tmp_vm_image)
                self.vnfs.append(tmp_res)

                # send the status to the SMR (not necessary)
                self.manoconn.publish(topic='specific.manager.registry.ssm.status', message=yaml.dump(
                    {'name': self.specific_manager_id, 'status': "IP address:'{0}'".format(host_ip)}))

            '''
            Now that you have the intended VNF's IP address, it is possible to configure/reconfigure the VNF either by ssh
            to the VNF or through a REST API - depends on how the VNF is designed.
            '''
            self.manoconn.notify(topic=self.amqp_topic, msg=yaml.dump({'name': self.specific_manager_id, 'IP': host_ip}))

            playbook_path = os.path.abspath('./ansible/site.yml')
            variable_manager = VariableManager()
            loader = DataLoader()
            host_list = [x['id'] for x in self.vnfs]
            inventory = Inventory(loader=loader,
                                  variable_manager=variable_manager,
                                  host_list=host_list)


            if not os.path.exists(playbook_path):
                LOG.error('The playbook %s does not exist', playbook_path)
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
                              syntax=False, connection='docker', module_path=None,
                              forks=10, remote_user='root',
                              private_key_file=None, ssh_common_args=None,
                              ssh_extra_args=None, sftp_extra_args=None,
                              scp_extra_args=None, become=False,
                              become_method='sudo', become_user='root',
                              verbosity=8, check=False)

            variable_manager.extra_vars = {'target': host_list[0], 'vnfs': self.vnfs}
            variable_manager.set_inventory(inventory)

            # play = PlaybookCLI(args=['/usr/local/bin/ansible-playbook', '-vvvv', '-i', '/tmp/i.txt', 'ansible/site.yml'])
            # play.parse()
            # results = play.run()

            LOG.warning('Executin playbook for hosts=%s, target=%s', host_list, host_list)
            pbex = PlaybookExecutor(playbooks=[playbook_path],
                                    inventory=inventory,
                                    variable_manager=variable_manager,
                                    loader=loader, options=options,
                                    passwords=None)
            results = pbex.run()

            # callback = CallbackModule() # SampleCallback()
            # pbex._tqm._stdout_callback = callback
            # return_code = pbex.run()
            # results = callback.results
            # results = return_code

            LOG.debug("Results=%s", results)
            return



def main():
    sonfsmvprxsquidconfiguration1()
    while True:
        time.sleep(1)

if __name__ == '__main__':
    main()
