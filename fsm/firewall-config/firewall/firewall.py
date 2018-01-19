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
import os
import time
import yaml
import paramiko
import tempfile
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.executor.playbook_executor import PlaybookExecutor
from sonsmbase.smbase import sonSMbase

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


class FirewallFSM(sonSMbase):

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

        self.specific_manager_type = 'fsm'
        self.service_name = 'psa-service'
        self.function_name = 'firewall-vnf'
        self.specific_manager_name = 'firewall-config'
        self.id_number = '1'
        self.version = 'v0.1'
        self.description = "An FSM that subscribes to start, stop and configuration topic for Firewall VNF"

        self.is_running_in_emulator = 'SON_EMULATOR' in os.environ
        LOG.debug('Running in the emulator is %s', self.is_running_in_emulator)
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
        topic = "generic.fsm." + str(self.sfuuid)
        self.manoconn.subscribe(self.message_received, topic)
        LOG.info("Subscribed to " + topic + " topic.")

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
            topic = "generic.fsm." + str(self.sfuuid)
            corr_id = props.correlation_id
            self.manoconn.notify(topic,
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
        mgmt_ip = None
        vm_image = 'http://files.sonata-nfv.eu/son-psa-pilot/pfSense-vnf/' \
                       'pfSense.qcow2'

        if (vnfr['virtual_deployment_units']
                    [0]['vm_image']) == vm_image:
             mgmt_ip = (vnfr['virtual_deployment_units']
                        [0]['vnfc_instance'][0]['connection_points'][0]
                        ['interface']['address'])

        if not mgmt_ip:
            LOG.error("Couldn't obtain mgmt IP address from VNFR during start")
            return

        ssh = self._create_ssh_connection(mgmt_ip)
        if not ssh:
            LOG.error('Unable to establish an SSH connection during the start event')
            return;

        #activate firewall
        #command = "pfctl -e"
        #(stdin, stdout, stderr) = ssh.exec_command(command)
        #LOG.debug('Stdout: ' + str(stdout))
        #LOG.debug('Stderr: ' + str(stderr))
        #ssh.close()

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

        vnfr = content["vnfr"]
        mgmt_ip = None
        vm_image = 'http://files.sonata-nfv.eu/son-psa-pilot/pfSense-vnf/' \
                       'pfSense.qcow2'


        if (vnfr['virtual_deployment_units']
                    [0]['vm_image']) == vm_image:
             mgmt_ip = (vnfr['virtual_deployment_units']
                           [0]['vnfc_instance'][0]['connection_points'][0]
                           ['interface']['address'])

        if not mgmt_ip:
            LOG.error("Couldn't obtain IP address from VNFR during stop")
            return

        ssh = self._create_ssh_connection(mgmt_ip)
        if not ssh:
            LOG.error('Unable to establish an SSH connection during the stop event')
            return;

        #desactivate firewall
        #command = "pfctl -d"
        #(stdin, stdout, stderr) = ssh.exec_command(command)
        #LOG.debug('Stdout: ' + str(stdout))
        #LOG.debug('Stderr: ' + str(stderr))
        #ssh.close()
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

        mgmt_ip = None
        next_ip = None
        vm_image = 'http://files.sonata-nfv.eu/son-psa-pilot/pfSense-vnf/' \
                       'pfsense.qcow2'

        #sp address (retrieve it from NSR)
        #sp_ip = 'sp.int3.sonata-nfv.eu'
        sp_ip = '10.30.0.112'

        if content['management_ip']:
            mgmt_ip = content['management_ip']

        if content['next_ip']:
            next_ip=content['next_ip']

        if not mgmt_ip:
            LOG.error("Couldn't obtain mgmt IP address from VNFR during configuration")
            return

        ssh = self._create_ssh_connection(mgmt_ip)
        if not ssh:
            LOG.error('Unable to establish an SSH connection during the configure event')
            return;


        LOG.info("Retrieve FSM IP address")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            "echo $SSH_CLIENT | awk '{ print $1}'")
        sout = ssh_stdout.read().decode('utf-8')
        serr = ssh_stderr.read().decode('utf-8')
        LOG.info("stdout: {0}\nstderr:  {1}"
                 .format(sout, serr))
        fsm_ip = sout.strip()
        LOG.info("FSM IP: {0}".format(fsm_ip))

        LOG.info("Get current default GW")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            "/usr/bin/netstat -nr| awk '/default/ { print $2 }'")
        sout = ssh_stdout.read().decode('utf-8')
        serr = ssh_stderr.read().decode('utf-8')
        LOG.info("stdout: {0}\nstderr:  {1}"
                 .format(sout, serr))
        default_gw = sout.strip()
        LOG.info("Default GW: {0}".format(str(default_gw)))

        LOG.info("Configure route for FSM IP")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            "route add {0} {1}"
            .format(fsm_ip, default_gw))
        LOG.info("stdout: {0}\nstderr:  {1}"
                 .format(ssh_stdout.read().decode('utf-8'),
                         ssh_stderr.read().decode('utf-8')))


        LOG.info("Configure route for monitoring ")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            "route add {0} {1}"
            .format(sp_ip, default_gw))
        LOG.info("stdout: {0}\nstderr:  {1}"
                 .format(ssh_stdout.read().decode('utf-8'),
                         ssh_stderr.read().decode('utf-8')))

        LOG.info("Always use ethO (mgmt) for connection from 10.230.x.x for debug")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            "route add -net 10.230.0.0/16 {0}".format(default_gw))
        LOG.info("stdout: {0}\nstderr:  {1}"
                 .format(ssh_stdout.read().decode('utf-8'),
                         ssh_stderr.read().decode('utf-8')))

        # remove default GW
        LOG.info("Delete default GW")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            "route del default")
        LOG.info("stdout: {0}\nstderr:  {1}"
                 .format(ssh_stdout.read().decode('utf-8'),
                         ssh_stderr.read().decode('utf-8')))

        # if next VNF do not exists use vtnet2 (wan) gateway stored by pfSense
        if not next_ip:
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
                "cat /tmp/vtnet2_router")
            sout = ssh_stdout.read().decode('utf-8')
            serr = ssh_stderr.read().decode('utf-8')
            LOG.info("stdout: {0}\nstderr:  {1}"
                     .format(sout, serr))
            next_ip = sout.strip()
            LOG.info("New default GW: {0}".format(str(next_ip)))

        LOG.info("Configure default GW for next VNF or gateway"
                     .format(next_ip))
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
                "route add default {0}".format(next_ip))
        LOG.info("stdout: {0}\nstderr:  {1}"
                     .format(ssh_stdout.read().decode('utf-8'),
                             ssh_stderr.read().decode('utf-8')))


        #Activate firewall
        #command = "pfctl -e" 
        #(stdin, stdout, stderr) = ssh.exec_command(command)
        #LOG.debug('Stdout: ' + str(stdout))
        #LOG.debug('Stderr: ' + str(stderr))

        ssh.close()


        #Configure and activate monitoring probe

        self.createConf(sp_ip, 4, 'vfw-vnf')
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(mgmt_ip, port, 'sonata', 'sonata',look_for_keys=False, timeout=5)
        sftp = ssh.client.open_sftp()
        sftp.put('node.conf', '/home/sonata/monitoring/node.conf')
        sftp.close()
        command = "/etc/rc.d/sonmonprobe start" 
        (stdin, stdout, stderr) = ssh.exec_command(command)
        ssh.close()


        # Create a response for the FLM
        response = {}
        response['status'] = 'COMPLETED'

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

    def fw_configure(self, fw_vnfr):
        fw_cpinput_ip = '10.30.0.2'
        fw_cpinput_netmask = '255.255.255.252'
        fw_cpinput_network = '10.30.0.2/30'

        # configure vm using ansible playbook
        loader = DataLoader()
        with tempfile.NamedTemporaryFile() as fp:
            fp.write(b'[firewallserver]\n')
            if self.is_running_in_emulator:
                fp.write(b'mn.vnf_fw')
            else:
                fp.write(mgmt_ip.encode('utf-8'))
            fp.flush()
            inventory = InventoryManager(loader=loader, sources=[fp.name])
        variable_manager = VariableManager(loader=loader, inventory=inventory)
        playbook_path = os.path.abspath('./ansible/site.yml')
        LOG.debug('Targeting the ansible playbook: %s', playbook_path)
        if not os.path.exists(playbook_path):
            LOG.error('The playbook does not exist')
            return False
        Options = namedtuple('Options',
                             ['listtags', 'listtasks', 'listhosts',
                              'syntax', 'connection', 'module_path',
                              'forks', 'remote_user', 'private_key_file',
                              'ssh_common_args', 'ssh_extra_args',
                              'sftp_extra_args', 'scp_extra_args',
                              'become', 'become_method', 'become_user',
                              'verbosity', 'check', 'diff'])
        options = Options(listtags=False, listtasks=False, listhosts=False,
                          syntax=False, connection='ssh', module_path=None,
                          forks=100, remote_user='slotlocker',
                          private_key_file=None, ssh_common_args=None,
                          ssh_extra_args=None, sftp_extra_args=None,
                          scp_extra_args=None, become=True,
                          become_method=None, become_user='root',
                          verbosity=None, check=False, diff=True)
        options = options._replace(connection='docker', become=False)
        variable_manager.extra_vars = {'FW_CPINPUT_NETWORK': fw_cpinput_network,
                                       'SON_EMULATOR': self.is_running_in_emulator }
        pbex = PlaybookExecutor(playbooks=[playbook_path],
                                inventory=inventory,
                                variable_manager=variable_manager,
                                loader=loader, options=options,
                                passwords={})
        results = pbex.run()
        return True

    def _create_ssh_connection(self, mgmt_ip):
        port = 22
        username = 'root'
        password = 'pfsense'
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        num_retries = 30
        retry = 0
        while retry < num_retries:
            try:
                ssh.connect(mgmt_ip, port, username, password)
                break
            except paramiko.BadHostKeyException as e:
                LOG.info("Bad entry in ~/.ssh/known_hosts: %s", e)
                time.sleep(1)
                retry += 1
            except EOFError:
                LOG.info('Unexpected Error from SSH Connection, retry in 5 seconds')
                time.sleep(10)
                retry += 1
            except Exception as e:
                LOG.info('SSH Connection refused from %s, will retry in 5 seconds (%s)', mgmt_ip, e)
                time.sleep(10)
                retry += 1

        if retry == num_retries:
            LOG.error('Could not establish SSH connection within max retries')
            return None;
        return ssh


    #create conf for monitoring
    def createConf(self, pw_ip, interval, name):
        config = configparser.RawConfigParser()
        config.add_section('vm_node')
        config.add_section('Prometheus')
        config.set('vm_node', 'node_name', name)
        config.set('vm_node', 'post_freq', interval)
        config.set('Prometheus', 'server_url', 'http://'+pw_ip+':9091/metrics')

        with open('node.conf', 'w') as configfile:    # save
            config.write(configfile)
        f = open('node.conf', 'r')
        LOG.debug('Mon Config-> '+"\n"+f.read())
        f.close()



def main(working_dir=None):
    if working_dir:
        os.chdir(working_dir)
    LOG.info('Welcome to the main in %s', __name__)
    FirewallFSM()
    while True:
        time.sleep(10)


if __name__ == '__main__':
    main()
