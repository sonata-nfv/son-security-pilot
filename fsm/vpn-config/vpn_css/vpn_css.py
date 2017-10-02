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

import time
import logging
import yaml
import paramiko
import os
import sys
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.executor.playbook_executor import PlaybookExecutor
from sonsmbase.smbase import sonSMbase

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


class CssFSM(sonSMbase):

    _listening_topic_root = ('generic', 'fsm')

    @staticmethod
    def get_listening_topic_name():
        return '.'.join(CssFSM._listening_topic_root)

    def __init__(self):

        """
        :param specific_manager_type: specifies the type of specific manager
        that could be either fsm or ssm.
        :param service_name: the name of the service that this specific manager
        belongs to.
        :param function_name: the name of the function that this specific
        manager belongs to, will be null in SSM case
        :param specific_manager_name: the actual name of specific manager
        (e.g., scaling, placement)
        :param id_number: the specific manager id number which is used to
        distinguish between multiple SSM/FSM that are created for the same
        objective (e.g., scaling with algorithm 1 and 2)
        :param version: version
        :param description: description
        """

        LOG.debug('Initialize CssFSM from %s', __file__)
        self.specific_manager_type = 'fsm'
        self.service_name = 'service1'
        self.function_name = 'function1'
        self.specific_manager_name = 'css'
        self.id_number = '1'
        self.version = 'v0.1'
        self.topic = ''
        self.description = "An FSM that subscribes to start, stop and configuration topic"

        super(self.__class__, self).__init__(specific_manager_type=self.specific_manager_type,
                                             service_name=self.service_name,
                                             function_name=self.function_name,
                                             specific_manager_name=self.specific_manager_name,
                                             id_number=self.id_number,
                                             version=self.version,
                                             description=self.description)

    def on_registration_ok(self):

        # The fsm registration was successful
        LOG.debug("Received registration ok event.")

        # send the status to the SMR
        status = 'Subscribed, waiting for alert message'
        message = {'name': self.specific_manager_id,
                   'status': status}
        self.manoconn.publish(topic='specific.manager.registry.ssm.status',
                              message=yaml.dump(message))

        # Subscribing to the topics that the fsm needs to listen on
#        topic = CssFSM.get_listening_topic_name()
        self.topic = 'generic.fsm.' + self.sfuuid
        self.manoconn.subscribe(self.message_received, self.topic)
        LOG.info("Subscribed to " + self.topic + " topic.")

    def message_received(self, ch, method, props, payload):
        """
        This method handles received messages
        """

        LOG.debug('<-- message_received app_id=%s', props.app_id)
        # Decode the content of the message
        request = yaml.load(payload)

        # Don't trigger on non-request messages
        if "fsm_type" not in request.keys():
            LOG.info("Received a non-request message, ignoring...")
            return
        LOG.info('Handling message with fsm_type=%s', request["fsm_type"])

        # Create the response
        response = None

        # the 'fsm_type' field in the content indicates for which type of
        # fsm this message is intended. In this case, this FSM functions as
        # start, stop and configure FSM
        if str(request["fsm_type"]) == "start":
            LOG.info("Start event received: " + str(request["content"]))
            response = self.start_event(request["content"])

        if str(request["fsm_type"]) == "stop":
            LOG.info("Stop event received: " + str(request["content"]))
            response = self.stop_event(request["content"])

        if str(request["fsm_type"]) == "configure":
            LOG.info("Config event received: " + str(request["content"]))
            response = self.configure_event(request["content"])

        if str(request["fsm_type"]) == "scale":
            LOG.info("Scale event received: " + str(request["content"]))
            response = self.scale_event(request["content"])

        # If a response message was generated, send it back to the FLM
        if response is not None:
            # Generated response for the FLM
            LOG.info("Response to request generated:" + str(response))
            # topic = CssFSM.get_listening_topic_name()
            corr_id = props.correlation_id
            self.manoconn.notify(self.topic,
                                 yaml.dump(response),
                                 correlation_id=corr_id)
            return

        # If response is None:
        LOG.info("Request received for other type of FSM, ignoring...")

    def start_event(self, content):
        """
        This method handles a start event.
        """
        LOG.info("Performing life cycle start event")
        LOG.info("content: " + str(content.keys()))
        # TODO: Add the start logic. The content is a dictionary that contains
        # the required data

        vnfr = content["vnfr"]
        vnfd = content["vnfd"]
        LOG.info("VNFR: " + yaml.dump(vnfr))

        vdu = vnfr['virtual_deployment_units'][0]
        cps = vdu['vnfc_instance'][0]['connection_points']

        man_ip = None
        for cp in cps:
            if cp['type'] == 'management':
                man_ip = cp['interface']['address']
                LOG.info("management ip: " + str(man_ip))

        if man_ip is not None:
            username = "root"
            password = "natoar32"

            ssh = paramiko.SSHClient()
            LOG.info("SSH client started")

            ssh.connect(man_ip, username=username, password=password)
            LOG.info("SSH connection established")

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('ls')
            LOG.info('output from remote: ' + str(ssh_stdout))
            LOG.info('output from remote: ' + str(ssh_stdin))
            LOG.info('output from remote: ' + str(ssh_stderr))
        else:
            LOG.info("No management connection point in vnfr")

        # Create a response for the FLM
        response = {}
        response['status'] = 'COMPLETED'

        # TODO: complete the response

        return response

    def stop_event(self, content):
        """
        This method handles a stop event.
        """
        LOG.info("Performing life cycle stop event")
        LOG.info("content: " + str(content.keys()))
        # TODO: Add the stop logic. The content is a dictionary that contains
        # the required data

        vnfr = content['vnfr']

        # Create a response for the FLM
        response = {}
        response['status'] = 'COMPLETED'

        # TODO: complete the response

        return response

    def configure_event(self, content):
        """
        This method handles a configure event.
        """
        LOG.info("Performing life cycle configure event")
        LOG.info("content: " + str(content.keys()))
        # TODO: Add the configure logic. The content is a dictionary that
        # contains the required data

        nsr = content['nsr']
        vnfrs = content['vnfrs']

        result = self.vpn_configure(vnfrs[0])

        # Create a response for the FLM
        response = {}
        response['status'] = 'COMPLETED' if result else 'ERROR'

        # TODO: complete the response

        return response

    def scale_event(self, content):
        """
        This method handles a scale event.
        """
        LOG.info("Performing life cycle scale event")
        LOG.info("content: " + str(content.keys()))
        # TODO: Add the configure logic. The content is a dictionary that
        # contains the required data

        # Create a response for the FLM
        response = {}
        response['status'] = 'COMPLETED'

        # TODO: complete the response

        return response

    def vpn_configure(self, vnfr):

        LOG.info('Start retrieving the IP address ...')

        vdu = vnfr['virtual_deployment_units'][0]
        cps = vdu['vnfc_instance'][0]['connection_points']

        mgmt_ip = None
        for cp in cps:
            if cp['type'] == 'management':
                mgmt_ip = cp['interface']['address']
                LOG.info("management ip: " + str(mgmt_ip))

        if not mgmt_ip:
            LOG.error("Couldn't obtain IP address from VNFR")
            return

        LOG.info("IP address:'{0}'".format(mgmt_ip))

        # configure vm using ansible playbook
        variable_manager = VariableManager()
        loader = DataLoader()

        inventory = InventoryManager(loader=loader,
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
    LOG.info('Welcome to the main in %s', __name__)
    CssFSM()
    while True:
        time.sleep(10)


if __name__ == '__main__':
    main()
