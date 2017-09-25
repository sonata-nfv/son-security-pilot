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
LOG = logging.getLogger("ssm-portal-configure-1")
LOG.setLevel(logging.DEBUG)
logging.getLogger("son-mano-base:messaging").setLevel(logging.INFO)


class Portal_Configure(sonSMbase):

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
        self.service_name = 'psa'
        self.specific_manager_name = 'portal-configure'
        self.id_number = '1'
        self.version = 'v0.1'
        self.counter = 0
        self.nsd = None
        self.vnfs = None
        self.description = "An empty SSM"

        super(self.__class__, self).__init__(specific_manager_type= self.specific_manager_type,
                                             service_name= self.service_name,
                                             specific_manager_name = self.specific_manager_name,
                                             id_number = self.id_number,
                                             version = self.version,
                                             description = self.description)
        self.setup_portal_conn()
        self.run()

    def on_registration_ok(self):
        LOG.info("Received registration ok event.")
        self.manoconn.publish(topic='specific.manager.registry.ssm.status', message=yaml.dump(
                                  {'name':self.specific_manager_id,'status': 'UP and Running'}))

        # Subscribe to the topic that the SLM will be sending on
        topic = 'generic.ssm.' + self.sfuuid
        self.manoconn.subscribe(self.received_request, topic)

    def setup_portal_conn(self):
        """
        Setup the connection with the portal.
        """

        # TODO: setup the connection with the portal
        pass

    def run(self):
        """
        Start waiting for messages from portal.
        """

        self.get_from_portal()

    def get_from_portal(self):
        """
        This method handles data coming from portal to SSM.
        """

        # TODO: screen for messages
        content = {}

        # Start SSM process
        self.on_input_from_portal(content)

    def push_to_portal(self, content):
        """
        This method handles data going from the SSM to the portal.
        """

        # TODO: inform portal when changes to psa configuration occured.
        pass

    def on_input_from_portal(self, content):
        """
        This method is called when the SSM receives a request from the portal.
        """

        # TODO: create request for SLM based on content from portal
        nsd = {}
        vnfds = [{}, {}, {}]

        request = {}
        request['shedule'] = ["vnf_chain", "inform_ssm"]
        request['payload'] = {'nsd': nsd, 'vnfds': vnfds}

        # Make request to SLM
        topic = 'generic.ssm.' + self.sfuuid
        self.manoconn.call_async(self.slm_response,
                                 topic,
                                 yaml.dump(request))

    def slm_response(self, ch, method, prop, payload):
        """
        This method handles the response from the SLM on the request to change
        the chaining of the psa service.
        """

        content = yaml.load(payload)

        # TODO: Interact with the portal
        data = {}
        self.push_to_portal(data)


def main():
    Portal_Configure()

if __name__ == '__main__':
    main()
