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
import configparser
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.executor.playbook_executor import PlaybookExecutor
from sonsmbase.smbase import sonSMbase

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

class faceFSM(sonSMbase):

    username = 'sonata'
    #keyfile = '../ansible/roles/squid/files/sonata.pem'
    password = 'sonata'
    monitoring_file = './node.conf'
    alternate_squid_cfg_file = './ansible/roles/squid/files/squid.conf'
    with_monitoring = True
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
    
        #if 'KEYFILE' in os.environ:
         #   keyfile = os.environ['KEYFILE'] 

        self.specific_manager_type = 'fsm'
        #self.service_name = 'psa'
        #self.function_name = 'proxy'
        self.specific_manager_name = 'prx-config'
        self.service_name = 'psaservice'
        self.function_name = 'prx-vnf'
        self.id_number = '1'
        self.version = 'v0.1'
        self.description = 'FSM that implements the subscription of the start, stop, configuration topics'
        self.topic = ''

                
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
        self.topic = "generic.fsm." + str(self.sfuuid)
        self.manoconn.subscribe(self.message_received, self.topic)
        LOG.info("Subscribed to " + self.topic + " topic.")
        
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
#        if self.private_key == None:
#            LOG.info("private key with value null")
#            return
        
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
            #topic = "generic.fsm." + str(self.sfuuid)
            corr_id = props.correlation_id
            self.manoconn.notify(self.topic,
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
            if self.option == 0:
                self.playbook_execution(plbk, squid_ip)
            else:
                opt = 0
                self.ssh_execution(opt, squid_ip)
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
            if self.option == 0:
                self.playbook_execution(plbk, squid_ip)
            else:
                opt = 1
                self.ssh_execution(opt, squid_ip)
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
            if self.option == 0:
                self.playbook_execution(plbk, squid_ip)
            else:
                opt = 2
                self.ssh_execution(opt, squid_ip)

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
            if self.option == 0:
                self.playbook_execution(plbk, squid_ip)
            else:
                opt = 3
                self.ssh_execution(opt, squid_ip)

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

        num_retries = 20
        
        ssh = paramiko.SSHClient()
        LOG.info("SSH client start for user %s" self.username)

        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.load_system_host_keys()
        retry = 0
        while retry < num_retries:
            try:
#                ssh.connect(host_ip, username = self.username, pkey  = self.private_key)
                ssh.connect(host_ip, username = self.username, password  = self.password)
                break

            except paramiko.BadHostKeyException:
                LOG.info("%s has an entry in ~/.ssh/known_hosts and it doesn't match" % self.server.hostname)
                retry += 1
            except EOFError:
                LOG.info('Unexpected Error from SSH Connection, retry in 5 seconds')
                time.sleep(10)
                retry += 1
            except:
                LOG.info('SSH Connection refused from %s, will retry in 5 seconds', host_ip)
                time.sleep(10)
                retry += 1

        if retry == num_retries:
            LOG.info('Could not establish SSH connection within max retries')
            return;

        if function == 0:

            LOG.info("SSH connection established")

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo service squid start')
            LOG.info('output from remote: ' + str(ssh_stdout))
            LOG.info('output from remote: ' + str(ssh_stdin))
            LOG.info('output from remote: ' + str(ssh_stderr))
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo mv /opt/monitoring /opt/Monitoring')
            LOG.info('output from remote: ' + str(ssh_stdout))
            LOG.info('output from remote: ' + str(ssh_stdin))
            LOG.info('output from remote: ' + str(ssh_stderr))
            ssh.close()

            retry = 0
            if self.with_monitoring == True:
                transport = paramiko.Transport((host_ip, 22))
                while retry < num_retries:
                    try:
#                        ssh_stdin, ssh_stdout, ssh_stderr = transport.connect(username = self.username, pkey = self.private_key)
                        ssh_stdin, ssh_stdout, ssh_stderr = transport.connect(username = self.username, password = self.password)
                        break
                    except paramiko.BadHostKeyException:
                        LOG.info("%s has an entry in ~/.ssh/known_hosts and it doesn't match" % self.server.hostname)
                        retry += 1
                    except EOFError:
                        LOG.info('Unexpected Error from SSH Connection, retry in 5 seconds')
                        time.sleep(10)
                        retry += 1
                    except:
                        LOG.info('SSH Connection refused, will retry in 5 seconds')
                        time.sleep(10)
                        retry += 1

                if retry == num_retries:
                    LOG.info('Could not establish SSH connection within max retries for transport purposes')
                    return;

                LOG.info("SFTP connection established")
                LOG.info('output from remote: ' + str(ssh_stdout))
                LOG.info('output from remote: ' + str(ssh_stdin))
                LOG.info('output from remote: ' + str(ssh_stderr))

                self.createConf(host_ip, 4, 'cache-vnf')
                sftp = paramiko.SFTPClient.from_transport(transport)
                LOG.info("SFTP connection entering")
                localpath = self.monitoring_file
                remotepath = '/tmp'
                ssh_stdin, ssh_stdout, ssh_stderr = sftp.put(localpath, remotepath)
                LOG.info('output from remote: ' + str(ssh_stdout))
                LOG.info('output from remote: ' + str(ssh_stdin))
                LOG.info('output from remote: ' + str(ssh_stderr))
                sftp.close()
                transport.close()

                ssh = paramiko.SSHClient()

                retry = 0
                while retry < num_retries:
                    try:
#                        ssh.connect(host_ip, username = self.username, pkey = self.private_key)
                        ssh.connect(host_ip, username = self.username, password = self.password)
                        break
                    except paramiko.BadHostKeyException:
                        LOG.info("%s has an entry in ~/.ssh/known_hosts and it doesn't match" % self.server.hostname)
                        retry += 1
                    except EOFError:
                        LOG.info('Unexpected Error from SSH Connection, retry in 5 seconds')
                        time.sleep(10)
                        retry += 1
                    except:
                        LOG.info('SSH Connection refused, will retry in 5 seconds')
                        time.sleep(10)
                        retry += 1

                if retry == num_retries:
                    LOG.info('Could not establish SSH connection within max retries for monitoring start purposes')
                    return;

                LOG.info("SSH connection established")
                ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo cp /tmp/node.conf /opt/Monitoring')
                LOG.info('output from remote: ' + str(ssh_stdout))
                LOG.info('output from remote: ' + str(ssh_stdin))
                LOG.info('output from remote: ' + str(ssh_stderr))
                ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo systemctl restart mon-probe.service')
                LOG.info('output from remote: ' + str(ssh_stdout))
                LOG.info('output from remote: ' + str(ssh_stdin))
                LOG.info('output from remote: ' + str(ssh_stderr))
                ssh.close()



        elif function == 1:
            LOG.info("SSH client stop")

            LOG.info("SSH connection established")

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo service squid stop')
            LOG.info('output from remote: ' + str(ssh_stdout))
            LOG.info('output from remote: ' + str(ssh_stdin))
            LOG.info('output from remote: ' + str(ssh_stderr))
            ssh.close()

        elif function == 2:
            LOG.info("SSH client configure")
            LOG.info("SSH connection established")
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo service squid stop')
            LOG.info('output from remote: ' + str(ssh_stdout))
            LOG.info('output from remote: ' + str(ssh_stdin))
            LOG.info('output from remote: ' + str(ssh_stderr))
            ssh.close()
            
            transport = paramiko.Transport((host_ip, 22))
            while retry < num_retries:
                try:
#                    ssh_stdin, ssh_stdout, ssh_stderr = transport.connect(username = self.username, pkey = self.private_key)
                    ssh_stdin, ssh_stdout, ssh_stderr = transport.connect(username = self.username, password = self.password)
                    break
                except paramiko.BadHostKeyException:
                    LOG.info("%s has an entry in ~/.ssh/known_hosts and it doesn't match" % self.server.hostname)
                    retry += 1
                except EOFError:
                    LOG.info('Unexpected Error from SSH Connection, retry in 5 seconds')
                    time.sleep(10)
                    retry += 1
                except:
                    LOG.info('SSH Connection refused, will retry in 5 seconds')
                    time.sleep(10)
                    retry += 1

            if retry == num_retries:
                LOG.info('Could not establish SSH connection within max retries for transport purposes')
                return;

            LOG.info("SFTP connection established")
            LOG.info('output from remote: ' + str(ssh_stdout))
            LOG.info('output from remote: ' + str(ssh_stdin))
            LOG.info('output from remote: ' + str(ssh_stderr))

            self.createConf(host_ip, 4, 'cache-vnf')
            sftp = paramiko.SFTPClient.from_transport(transport)
            LOG.info("SFTP connection entering")
            localpath = self.alternate_squid_cfg_file
            remotepath = '/tmp'
            ssh_stdin, ssh_stdout, ssh_stderr = sftp.put(localpath, remotepath)
            LOG.info('output from remote: ' + str(ssh_stdout))
            LOG.info('output from remote: ' + str(ssh_stdin))
            LOG.info('output from remote: ' + str(ssh_stderr))
            sftp.close()
            transport.close()

            ssh = paramiko.SSHClient()

            retry = 0
            while retry < num_retries:
                try:
#                    ssh.connect(host_ip, username = self.username, pkey = self.private_key)
                    ssh.connect(host_ip, username = self.username, password = self.password)
                    break
                except paramiko.BadHostKeyException:
                    LOG.info("%s has an entry in ~/.ssh/known_hosts and it doesn't match" % self.server.hostname)
                    retry += 1
                except EOFError:
                    LOG.info('Unexpected Error from SSH Connection, retry in 5 seconds')
                    time.sleep(10)
                    retry += 1
                except:
                    LOG.info('SSH Connection refused, will retry in 5 seconds')
                    time.sleep(10)
                    retry += 1

            if retry == num_retries:
                LOG.info('Could not establish SSH connection within max retries for monitoring start purposes')
                return;

            LOG.info("SSH connection established")
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo mv /etc/squid3/squid.conf /etc/squid3/squid.conf.old')
            LOG.info('output from remote: ' + str(ssh_stdout))
            LOG.info('output from remote: ' + str(ssh_stdin))
            LOG.info('output from remote: ' + str(ssh_stderr))
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo cp /tmp/squid.conf /etc/squid3')
            LOG.info('output from remote: ' + str(ssh_stdout))
            LOG.info('output from remote: ' + str(ssh_stdin))
            LOG.info('output from remote: ' + str(ssh_stderr))
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo service squid restart')
            LOG.info('output from remote: ' + str(ssh_stdout))
            LOG.info('output from remote: ' + str(ssh_stdin))
            LOG.info('output from remote: ' + str(ssh_stderr))
            ssh.close()

        elif function == 3:
            LOG.info("SSH client scale")

            LOG.info("SSH connection established")

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo service squid start')
            LOG.info('output from remote: ' + str(ssh_stdout))
            LOG.info('output from remote: ' + str(ssh_stdin))
            LOG.info('output from remote: ' + str(ssh_stderr))
            ssh.close()
        else:
            LOG.info("Invalid operation on FSM %s", function)
            return
        
    def createConf(self, pw_ip, interval, name):

        #config = configparser.RawConfigParser()
        config = configparser.ConfigParser(interpolation = None)
        config.add_section('vm_node')
        config.add_section('Prometheus')
        config.set('vm_node', 'node_name', name)
        config.set('vm_node', 'post_freq', interval)
        config.set('Prometheus', 'server_url', 'http://' + pw_ip + ':9091/metrics')
    
    
        with open('node.conf', 'w') as configfile:    # save
            config.write(configfile)
    
        f = open('node.conf', 'r')
        LOG.debug('Mon Config-> ' + "\n" + f.read())
        f.close()

    
def main():
    faceFSM()
    while True:
        time.sleep(10)

if __name__ == '__main__':
    main()
