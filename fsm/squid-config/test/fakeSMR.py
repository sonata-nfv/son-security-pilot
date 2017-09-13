'''
Created on Jun 13, 2017

@author: ubuntu
'''

import logging
import yaml
import time
from sonmanobase import messaging

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
logging.getLogger("son-mano-base:messaging").setLevel(logging.INFO)


class fakesmr(object):

    def __init__(self):

        self.name = 'fake-smr'
        self.version = '0.1-dev'
        self.description = 'description'
        self.end = False

        LOG.info("Init fakesmr")

        # create and initialize broker connection
        self.manoconn = messaging.ManoBrokerRequestResponseConnection(self.name)

        self.declare_subscriptions()
        self._run()

    def _run(self):
        # go into infinity loop
        while self.end == False:
            # LOG.info("_run, sleeping")
            time.sleep(1)

    def declare_subscriptions(self):
        """
        Declare topics to which we want to listen and define callback methods.
        """
        self.manoconn.register_async_endpoint(self.on_register_receive, 'specific.manager.registry.ssm.registration')

    def on_register_receive(self,ch, method, properties, payload):

        message = yaml.load(payload)

        response = {
            "status": "registered",
            "specific_manager_type": message['specific_manager_type'],
            "service_name": message['service_name'],
            "function_name": message['function_name'],
            "specific_manager_id": message['specific_manager_id'],
            "version": message['version'],
            "description": message['description'],
            "uuid": '64532',
            "sfuuid": '97456',
            "error": None
        }

        LOG.info(response)
        return yaml.dump(response)


def main():
    fakesmr()


if __name__ == '__main__':
    main()
