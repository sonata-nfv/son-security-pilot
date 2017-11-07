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

import os
import time
import logging
import tempfile
import yaml
import paramiko
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.executor.playbook_executor import PlaybookExecutor
from sonsmbase.smbase import sonSMbase

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

class faceFSM(sonSMbase):

    username = 'ubuntu'
    keyfile = '../ansible/roles/squid/files/son-install.pem'
    option = 1

    def __init__(self):
        LOG.debug('Initialization of faceFSM in %s', __file__)
        
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
    
        if 'KEYFILE' in os.environ:
            keyfile = os.environ['KEYFILE'] 

        self.specific_manager_type = 'fsm'
        #self.service_name = 'psa'
        #self.function_name = 'proxy'
        self.specific_manager_name = 'prx-config'
        self.service_name = 'psaservice'
        self.function_name = 'prx-vnf'
        self.id_number = '1'
        self.version = 'v0.1'
        self.description = 'FSM that implements the subscription of the start, stop, configuration topics'

                
        super(self.__class__, self).__init__(specific_manager_type = self.specific_manager_type,
                                             service_name = self.service_name,
                                             function_name = self.function_name,
                                             specific_manager_name = self.specific_manager_name,
                                             id_number = self.id_number,
                                             version = self.version,
                                             description = self.description)

    def on_registration_ok(self):
        LOG.debug("Received registration ok event for %s", __file__)
        
        state = "Subscription successful, I'm waiting for messages"
        message = {'name': self.specific_manager_id,
                   'status': state}
        self.manoconn.publish(topic = 'specific.manager.registry.ssm.status',
                              message = yaml.dump(message))
        topic = "generic.fsm." + str(self.sfuuid)
        self.manoconn.subscribe(self.message_received, topic)
        LOG.info("Subscribed to " + topic + " topic.")
        
    def message_received(self, ch, method, props, payload):
        LOG.debug("Received message in %s", __file__)
        """
        handling of the different possible messages
        """
        
        request = yaml.load(payload)
        if "fsm_type" not in request.keys():
            LOG.info("Received a non-request message, ignoring...")
            return
        
        response = None
        
        if str(request["fsm_type"]) == "start":
            LOG.info("Start event received: " + str(request["content"]))
            response = self.start_ev(request["content"])
        elif str(request["fsm_type"]) == "stop":
            LOG.info("Stop event received: " + str(request["content"]))
            response = self.stop_ev(request["content"])
        elif str(request["fsm_type"]) == "configure":
            LOG.info("Config event received: " + str(request["content"]))
            response = self.configure_ev(request["content"])
        elif str(request["fsm_type"]) == "scale":
            LOG.info("Scale event received: " + str(request["content"]))
            response = self.scale_ev(request["content"])
            
        if response is not None:
            # Generated response for the FLM
            LOG.info("Response to request generated:" + str(response))
            topic = "generic.fsm." + str(self.sfuuid)
            corr_id = props.correlation_id
            self.manoconn.notify(topic,
                                 yaml.dump(response),
                                 correlation_id = corr_id)
            return
        
        LOG.info("Request received for other type of FSM, ignoring...")
    
    def start_ev(self, content):
        LOG.info("Performing life cycle start event with content = %s", str(content.keys()))
        
        vnfr = content["vnfr"]
        vnfd = content["vnfd"]
        LOG.info("VNFR: " + yaml.dump(vnfr))

        vdu = vnfr['virtual_deployment_units'][0]
        cpts = vdu['vnfc_instance'][0]['connection_points']
        
        squid_ip = None
        for cp in cpts:
            if cp['type'] == 'management':
                squid_ip = cp['interface']['address']
                LOG.info("management ip: " + str(squid_ip))
                
                
        if squid_ip is not None:
            plbk = ''
            if option == 0:
                self.playbook_execution(plbk, squid_ip)
            else:
                self.ssh_execution(request["fsm_type"], squid_ip)
        else:
            LOG.info("No management connection point in vnfr")
            
        response = {}
        response['status'] = 'COMPLETED'
        
        return response
    
    def stop_ev(self, content):
        LOG.info("Performing life cycle stop event with content = %s", str(content.keys()))
        
        vnfr = content["vnfr"]
        vnfd = content["vnfd"]
        LOG.info("VNFR: " + yaml.dump(vnfr))

        vdu = vnfr['virtual_deployment_units'][0]
        cpts = vdu['vnfc_instance'][0]['connection_points']
        
        squid_ip = None
        for cp in cpts:
            if cp['type'] == 'management':
                squid_ip = cp['interface']['address']
                LOG.info("management ip: " + str(squid_ip))
                
                
        if squid_ip is not None:
            plbk = ''
            if option:
                self.playbook_execution(plbk, squid_ip)
            else:
                self.ssh_execution(request["fsm_type"], squid_ip)
        else:
            LOG.info("No management connection point in vnfr")
            
        response = {}
        response['status'] = 'COMPLETED'
        
        return response
    
    def configure_ev(self, content):
        LOG.info("Configuration event with content = %s", str(content.keys()))
        
        vnfr = content["vnfr"]
        vnfd = content["vnfd"]
        LOG.info("VNFR: " + yaml.dump(vnfr))

        vdu = vnfr['virtual_deployment_units'][0]
        cpts = vdu['vnfc_instance'][0]['connection_points']
        
        squid_ip = None
        for cp in cpts:
            if cp['type'] == 'management':
                squid_ip = cp['interface']['address']
                LOG.info("management ip: " + str(squid_ip))
                
        if squid_ip is not None:
            plbk = '../ansible/site.yml'
            if option == 0:
                self.playbook_execution(plbk, squid_ip)
            else:
                self.ssh_execution(request["fsm_type"], squid_ip)

        else:
            LOG.info("No management connection point in vnfr")
            
        response = {}
        response['status'] = 'COMPLETED'
        response['IP'] = squid_ip
        
        return response
    
    def scale_ev(self, content):
        LOG.info("Scale event with content = %s", str(content.keys()))
        
        vnfr = content["vnfr"]
        vnfd = content["vnfd"]
        LOG.info("VNFR: " + yaml.dump(vnfr))

        vdu = vnfr['virtual_deployment_units'][0]
        cpts = vdu['vnfc_instance'][0]['connection_points']
        
        squid_ip = None
        for cp in cpts:
            if cp['type'] == 'management':
                squid_ip = cp['interface']['address']
                LOG.info("management ip: " + str(squid_ip))
                
        if squid_ip is not None:
            plbk = ''
            if option == 0:
                self.playbook_execution(plbk, squid_ip)
            else:
                self.ssh_execution(request["fsm_type"], squid_ip)

        else:
            LOG.info("No management connection point in vnfr")
        
        response = {}
        response['status'] = 'COMPLETED'
        response['IP'] = squid_ip

        return response
        
    def playbook_execution(self, playbook, host_ip):
        LOG.info("Executing playbook: %s", playbook)
        
        loader = DataLoader()

        inventory = None
        with tempfile.NamedTemporaryFile() as fp:
            fp.write(host_ip.encode('utf-8'))
            fp.flush()
            inventory = InventoryManager(loader=loader, sources=[fp.name])

        variable_manager = VariableManager(loader = loadder, inventory = inventory)

        if not os.path.exists(playbook):
            LOG.error('The playbook %s does not exist', playbook)
            return

        Options = namedtuple('Options',
                             ['listtags', 'listtasks', 'listhosts',
                              'syntax', 'connection', 'module_path',
                              'forks', 'remote_user', 'private_key_file',
                              'ssh_common_args', 'ssh_extra_args',
                              'sftp_extra_args', 'scp_extra_args',
                              'become', 'become_method', 'become_user',
                              'verbosity', 'check'])
        options = Options(listtags = False, listtasks = False, listhosts = False,
                          syntax = False, connection = 'ssh', module_path = None,
                          forks = 100, remote_user = 'slotlocker',
                          private_key_file = None, ssh_common_args = None,
                          ssh_extra_args = None, sftp_extra_args = None,
                          scp_extra_args = None, become = True,
                          become_method = None, become_user = 'root',
                          verbosity = None, check = False)

        variable_manager.extra_vars = {'hosts': host_ip}

        passwords = {}

        pbex = PlaybookExecutor(playbooks = [playbook],
                                inventory = inventory,
                                variable_manager = variable_manager,
                                loader = loader,
                                options = options,
                                passwords = passwords)
        results = pbex.run()
        return
    
    def ssh_execution(self, function, host_ip):
        LOG.info("Executing ssh connection with function: %s", function)
        
        if function == "start":
            ssh = paramiko.SSHClient()
            LOG.info("SSH client start")

            ssh.connect(host_ip, username = username, key_filename = keyfile)
            LOG.info("SSH connection established")

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('service squid start')
            LOG.info('output from remote: ' + str(ssh_stdout))
            LOG.info('output from remote: ' + str(ssh_stdin))
            LOG.info('output from remote: ' + str(ssh_stderr))
            ssh.close()
        elif function == "stop":
            ssh = paramiko.SSHClient()
            LOG.info("SSH client stop")

            ssh.connect(host_ip, username = username, key_filename = keyfile)
            LOG.info("SSH connection established")

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('service squid stop')
            LOG.info('output from remote: ' + str(ssh_stdout))
            LOG.info('output from remote: ' + str(ssh_stdin))
            LOG.info('output from remote: ' + str(ssh_stderr))
            ssh.close()
        elif function == "configure":
            ssh = paramiko.SSHClient()
            LOG.info("SSH client configure")

            ssh.connect(host_ip, username = username, key_filename = keyfile)
            LOG.info("SSH connection established")

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('service squid restart')
            LOG.info('output from remote: ' + str(ssh_stdout))
            LOG.info('output from remote: ' + str(ssh_stdin))
            LOG.info('output from remote: ' + str(ssh_stderr))
            ssh.close()
        elif function == "scale":
            ssh = paramiko.SSHClient()
            LOG.info("SSH client scale")

            ssh.connect(host_ip, username = username, key_filename = keyfile)
            LOG.info("SSH connection established")

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('service squid start')
            LOG.info('output from remote: ' + str(ssh_stdout))
            LOG.info('output from remote: ' + str(ssh_stdin))
            LOG.info('output from remote: ' + str(ssh_stderr))
            ssh.close()
        else:
            LOG.info("Invalid operation on FSM %s", function)
            return
        
    
def main():
    faceFSM()
    while True:
        time.sleep(10)

if __name__ == '__main__':
    main()
