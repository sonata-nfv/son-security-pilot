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
from sonsmbase.smbase import sonSMbase

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("ssm-task_config-1")
LOG.setLevel(logging.DEBUG)
logging.getLogger("son-mano-base:messaging").setLevel(logging.INFO)


class TaskConfigMonitorSSM(sonSMbase):

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
        self.specific_manager_type = 'ssm'
        self.service_name = 'psaservice'
        self.specific_manager_name = 'task-config-monitor'
        self.id_number = '1'
        self.version = 'v0.1'
        self.counter = 0

        self.nsd = None
        self.nsr = None
        self.functions = {}
        self.vnfrs = []
        self.ingress = None
        self.egress = None

        self.description = "Task - Config SSM for the PSA."

        super(self.__class__, self).__init__(specific_manager_type= self.specific_manager_type,
                                             service_name= self.service_name,
                                             specific_manager_name = self.specific_manager_name,
                                             id_number = self.id_number,
                                             version = self.version,
                                             description = self.description)

    def on_registration_ok(self):
        LOG.info("Received registration ok event.")
        self.manoconn.publish(topic='specific.manager.registry.ssm.status', message=yaml.dump(
                                  {'name':self.specific_manager_id,'status': 'UP and Running'}))

        # Subscribe to the topic that the SLM will be sending on
        topic = 'generic.ssm.' + self.sfuuid
        self.manoconn.subscribe(self.received_request, topic)

    def received_request(self, ch, method, prop, payload):
        """
        This method is called when the SLM is reaching out
        """
        content = yaml.load(payload)

        # Don't react to self-sent messages
        if prop.app_id == self.specific_manager_id:
            LOG.info("Received self-sent message, ignoring...")
            return

        # Don't react to messages that are not a request
        if 'ssm_type' not in content.keys():
            LOG.info("Received message that is not a request, ignoring...")
            return

        if str(content['ssm_type']) == 'task':
            LOG.info("Received a task request")
            self.task_request(prop.correlation_id, content)
            return

        if str(content['ssm_type']) == 'configure':
            LOG.info("Received a configure request")
            self.configure_request(prop.correlation_id, content)
            return

        if str(content['ssm_type']) == 'monitor':
            LOG.info("Received a monitor request")
            self.monitor_request(prop.correlation_id, content)
            return

        # If the request type field doesn't match any of the above
        LOG.info("type " + str(content['ssm_type']) + " not covered by SSM")

    def task_request(self, corr_id, content):
        """
        This method handles a task request. A task request allows the SSM to
        change the tasks in the workflow of the SLM. For the vPSA, we wan to
        add a configuration phase: first we want to dictate the payload for the
        configration FSMs and then we want to trigger there config_event.
        """

        # Update the received schedule
        schedule = content['schedule']

        schedule.insert(7, 'vnfs_config')
        schedule.insert(7, 'configure_ssm')

        response = {'schedule': schedule, 'status': 'COMPLETED'}

        LOG.info("task request responded to: " + str(response))

        # Sending a response
        topic = 'generic.ssm.' + self.sfuuid
        self.manoconn.notify(topic,
                             yaml.dump(response),
                             correlation_id=corr_id)

    def configure_request(self, corr_id, content):
        """
        This method handles a configuration request. If the configuration
        request is made during the instantiation workflow, it means that
        the SSM needs to configure which VNF requires a config_event, and
        what the required payload is.
        """

        if content["workflow"] == 'instantiation':
            msg = "Received a configure request for the instantiation workflow"
            LOG.info(msg)
            self.configure_instantiation(corr_id, content)

    def configure_instantiation(self, corr_id, content):
        """
        This method creates the configure response for the instantiation
        workflow. It will set the trigger for a config_event for each VNF.
        The payload for the config_event is the generic one provided by the
        SP.
        """
        LOG.info("Configuration instantiation request: " + str(content))

        service = content['service']
        functions = content['functions']

        self.nsd = service['nsd']
        self.nsr = service['nsr']

        for function in functions:
            LOG.info("Adding vnf: " + str(function['vnfd']['name']))
            self.functions[function['vnfd']['name']] = {}
            self.functions[function['vnfd']['name']]['id'] = function['id']
            self.functions[function['vnfd']['name']]['vnfd'] = function['vnfd']
            self.functions[function['vnfd']['name']]['vnfr'] = function['vnfr']
            self.vnfrs.append(function['vnfr'])

            vdu = function['vnfr']['virtual_deployment_units'][0]
            cps = vdu['vnfc_instance'][0]['connection_points']

            for cp in cps:
                if cp['type'] in ['internal', 'external']:
                    own_ip = cp['interface']['address']

                if cp['type'] in ['management']:
                    management_ip = cp['interface']['address']

            self.functions[function['vnfd']['name']]['own_ip'] = own_ip
            self.functions[function['vnfd']['name']]['management_ip'] = management_ip
            self.functions[function['vnfd']['name']]['next_ip'] = None

            LOG.info("own_ip: " + str(own_ip))

        # Hardcode the next IPs for the instantiation
        LOG.info("keys in function: " + str(self.functions.keys()))
        for key in self.functions.keys():
            LOG.info("Function: " + str(self.functions[key]))
            if key == 'vpn-vnf':
                if 'tor-vnf' in self.functions.keys():
                    self.functions[key]['next_ip'] = self.functions['tor-vpn']['own_ip']
                else:
                    self.functions[key]['next_ip'] = None
            if key == 'tor-vnf':
                self.functions[key]['next_ip'] = None
            if key == 'prx-vnf':
                self.functions[key]['next_ip'] = self.functions['tor-vpn']['own_ip']

        # self.ingress = content['ingress']
        # self.egress = content['egress']

        response = self.create_configuration_message()

        LOG.info("Generated response: " + str(response))
        # Sending a response
        topic = 'generic.ssm.' + self.sfuuid
        self.manoconn.notify(topic,
                             yaml.dump(response),
                             correlation_id=corr_id)

    def configure_running(self, payload):
        """
        This method reconfigures the service. This is the method that the
        Portal Application should call. The payload contains a list that
        is ordered. Each VNF is represented by its name (based on the
        descriptor)
        """

        chain = payload['chain']

        for index in range(0, len(chain) - 1):
            current_vnf = chain[index]
            next_vnf = chain[index + 1]
            next_ip = self.functions[next_vnf]['own_ip']
            self.functions[current_vnf]['next_ip'] = next_ip

        last_vnf = chain[-1]
        self.functions[current_vnf]['next_ip'] = None

        response = self.create_configuration_message()
        LOG.info("Generated response: " + str(response))
        # TODO: send this to the SLM

    def create_configuration_message(self):
        """
        This method creates the payload for the configuration response to the
        SLM.
        """

        response = {}
        response['vnf'] = []

        for vnf in self.functions:
            LOG.info("VNF: " + str(vnf))
            LOG.info("Keys: " + str(vnf.keys()))
            LOG.info("id: " + str(vnf['id']))
            new_entry = {}
            id = vnf['id']
            new_entry['id'] = id 
            payload = {}
            payload['management_ip'] = vnf['management_ip']
            payload['own_ip'] = vnf['own_ip']
            payload['next_ip'] = vnf['next_ip']
            new_entry['configure'] = {'trigger': True,
                                      'payload': payload}

            response['vnf'].append(new_entry)

        return response

    def monitor_request(self, corr_id, content):
        """
        This method will be triggered when monitoring data is received.
        """
        # if 'nsd' in content.keys():
        #     LOG.info("Received descriptors")
        #     self.nsd = content['nsd']
        #     self.vnfs = content['vnfs']

        # else:
        #     if self.counter == 0:
        #         message = {}
        #         message['foo'] = 'bar'
        #         message['service_instance_id'] = self.sfuuid
        #         message['workflow'] = 'termination'

        #         # message['schedule'] = ['vnfs_scale']
        #         # message['vnf'] = []

        #         # for vnf in self.vnfs:
        #         #     if vnf['vnfd']['name'] == 'vtc-vnf':
        #         #         new_entry = {}
        #         #         new_entry['id'] = vnf['id']
        #         #         new_entry['scale'] = {'trigger': True,
        #         #                               'payload': {'foo': 'bar',
        #         #                                           'vnfr': 'bar'}}
        #         #         message['vnf'].append(new_entry)
        #         topic = 'monitor.ssm.' + self.sfuuid
        #         self.manoconn.notify(topic, yaml.dump(message))
        #         self.counter = 1
        #         LOG.info("Responded to monitoring request")

        pass


def main():
    TaskConfigMonitorSSM()

if __name__ == '__main__':
    main()
