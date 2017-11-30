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

import websocket
import _thread
import time
import sys
import pika

from threading import Thread
from websocket_server import WebsocketServer
from json import loads, dumps


logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("ssm-portal-configure-1")
LOG.setLevel(logging.DEBUG)
logging.getLogger("son-mano-base:messaging").setLevel(logging.INFO)


class Server:
    # Called for every client connecting (after handshake)
    def new_client(self, client, server):
        logging.warning("*********************"+"New client connected and was given id"+ str(client['id']))

    # Called for every client disconnecting
    def client_left(self, client, server):
        logging.warning("*********************"+"Client("+str(client['id'])+") disconnected")


    # Called when a client sends a message
    def message_received(self, client, server, message):
        if len(message) > 200:
            message = message[:200]+'..'
        logging.warning("*********************"+"Client("+str(client['id'])+") said:"+message)

        # Format message
        messageDict = loads(message)
        actionName = messageDict['name']

        def amqp_send():
            #self.manoconn.publish(topic='specific.manager.registry.ssm.status', message=yaml.dump(
            #                      {'name':self.specific_manager_id,'status': 'UP and Running'}))

            # Subscribe to the topic that the SLM will be sending on
            #topic = 'generic.ssm.' + str(self.sfuuid)
            #self.manoconn.subscribe(self.received_request, topic)

            credentials = pika.PlainCredentials('wolke', 'wolke')

            connection = pika.BlockingConnection(pika.ConnectionParameters(credentials=credentials,host='10.10.243.101'))

            channel = connection.channel()

            channel.queue_declare(queue='hello')

            channel.basic_publish(exchange='',
                                          routing_key='hello',
                                                                body='Hello World!')
            logging.warning(" [x] Sent 'Hello World!'")
            connection.close()

        #TODO relay request on queue and wait for response
        def sendMessage():
            logging.warning("*********************"+"Sending Message")
            amqp_send()
            logging.warning("*********************"+"Sending Message")
            amqp_send()
            toSend = None
            if actionName == "fsm start":
                fsmName = messageDict['Data']['name']
                fsmID = messageDict['Data']['id']
                toSend  = {"name": actionName, "Data": {
                    "name": fsmName,
                    "id": fsmID,
                    "state": "started"
                    }
                }

            if actionName == "fsm stop":
                fsmName = messageDict['Data']['name']
                fsmID = messageDict['Data']['id']
                toSend  = {"name": actionName, "Data": {
                    "name": fsmName,
                    "id": fsmID,
                    "state": "stopped"
                    }
                }

            if actionName == "basic start":
              logging.warning("*********************"+actionName)
              toSend  = {
                  "name": "basic start",
                  "data":
                  [
                      {"name": "Firewall", "id": "1", "state": "started"},
                      {"name": "VPN", "id": "2", "state": "started"}
                  ],
                  }

            if actionName == "basic stop":
              logging.warning("*********************"+actionName)
              toSend  = {
                  "name": "basic stop",
                  "data":
                  [
                      {"name": "Firewall", "id": "1", "state": "stopped"},
                      {"name": "VPN", "id": "2", "state": "stopped"}
                  ],
                  }


            if actionName == "anon start":
                logging.warning("*********************"+actionName)
                toSend  = {
                    "name": "anon start",
                    "data":
                    [
                      {"name": "Firewall", "id": "1", "state": "started"},
                      {"name": "VPN", "id": "2", "state": "started"},
                      {"name": "TOR", "id": "3", "state": "started"},
                      #{"name": "HTTP Proxy", "id": "4", "state": "started"},
                      {"name": "IDS", "id": "5", "state": "started"}
                    ],
                    }

            if actionName == "anon stop":
              logging.warning("*********************"+actionName)
              toSend  = {
                  "name": "anon stop",
                  "data":
                  [
                    {"name": "Firewall", "id": "1", "state": "stopped"},
                    {"name": "VPN", "id": "2", "state": "stopped"},
                    {"name": "TOR", "id": "3", "state": "stopped"},
                    #{"name": "HTTP Proxy", "id": "4", "state": "stopped"},
                    {"name": "IDS", "id": "5", "state": "stopped"}
                  ],
                  }

            try:
                toSendJson = dumps(toSend)
                logging.warning("*********************"+toSendJson)
                server.send_message(client, toSendJson)
            except Exception as e:
                logging.warning("*********************"+str(e))

        sendMessage()


    def listenToFSMRequests(self):
        #logging.warning("*********************","Listening to Requests...!")
        logging.warning("*********************Listening to Requests...!")
        port=9191
        host="0.0.0.0"
        #host="selfservice-ssm"
        server = WebsocketServer(port, host=host)
        server.set_fn_new_client(self.new_client)
        server.set_fn_client_left(self.client_left)
        server.set_fn_message_received(self.message_received)
        server.run_forever()




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
        topic = 'generic.ssm.' + str(self.sfuuid)
        self.manoconn.subscribe(self.received_request, topic)

    # Does this go here?
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
        for vnfr in vnfrs:
            if (vnfr['virtual_deployment_units'][0]['vm_image']) == 'http://files.sonata-nfv.eu/son-psa-pilot/vpn-vnf/sonata-vpn.qcow2':
                vpn_ip = vnfr['virtual_deployment_units'][0]['vnfc_instance'] [0]['connection_points'][0]['interface']['address']
                LOG.info("vVPN's management IP retrieved: "+vpn_ip)
                
            if (vnfr['virtual_deployment_units'][0]['vm_image']) == 'http://files.sonata-nfv.eu/son-psa-pilot/tor-vnf/sonata-tor.qcow2':
                tor_ip = vnfr['virtual_deployment_units'][0]['vnfc_instance'] [0]['connection_points'][0]['interface']['address']
                LOG.info("vTOR's management IP retrieved: "+tor_ip)

            # instead of sonata-prx, might be u16squid-micro-x86-64-v04.qcow2
            if (vnfr['virtual_deployment_units'][0]['vm_image']) == 'http://files.sonata-nfv.eu/son-psa-pilot/prx-vnf/sonata-prx.qcow2':
                prx_ip = vnfr['virtual_deployment_units'][0]['vnfc_instance'] [0]['connection_points'][0]['interface']['address']
                LOG.info("vProxy's management IP retrieved: "+prx_ip)

        try:
            iprev = reverse(vpn_ip)
            LOG.info("Got the reverse IP to be turned to integer: "+iprev)
            ipInt = int(netaddr.IPAddress(iprev))
            LOG.info("Got the Integer from the IP: "+str(ipInt))


        
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
        topic = 'generic.ssm.' + str(self.sfuuid)
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

    server = Server()

    Thread(target = server.listenToFSMRequests()).start()


if __name__ == '__main__':
    main()
