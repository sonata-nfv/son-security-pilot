'''
Created on Jun 13, 2017

@author: ubuntu
'''

import unittest
import yaml
import threading
import logging
import time
import sys

from multiprocessing import Process
import fakeFLM
import fakeSMR
from sonmanobase import messaging
# from configuration.configuration import ConfigurationFSM
import sonfsmvprxsquidconfiguration1.sonfsmvprxsquidconfiguration1

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.getLogger('amqpstorm').setLevel(logging.INFO)
# logging.getLogger("son-mano-base:messaging").setLevel(logging.INFO)
# FORMAT = '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s'
FORMAT = '[%(asctime)s] %(levelname)s [%(funcName)s:%(lineno)d] %(message)s'
logging.basicConfig(level=logging.DEBUG, format=FORMAT)
LOG = logging.getLogger(__name__)


class testConf(unittest.TestCase):

    def setUp(self):
        self.slm_proc = Process(target=fakeFLM.main)
        self.smr_proc = Process(target=fakeSMR.main)
        self.con_proc = Process(target=sonfsmvprxsquidconfiguration1.sonfsmvprxsquidconfiguration1.main)

        self.slm_proc.daemon = True
        self.smr_proc.daemon = True
        # self.con_proc.daemon = True

        self.manoconn = messaging.ManoBrokerRequestResponseConnection('ConfTest')

        self.wait_for_reg_event = threading.Event()
        self.wait_for_reg_event.clear()

        self.wait_for_res_event = threading.Event()
        self.wait_for_res_event.clear()

    def tearDown(self):
        LOG.info("tearDown")
        if self.smr_proc is not None:
            self.smr_proc.terminate()
        del self.smr_proc

        if self.slm_proc is not None:
            self.slm_proc.terminate()
        del self.slm_proc

        if self.con_proc is not None:
            self.con_proc.terminate()
        del self.con_proc

        try:
            self.manoconn.stop_connection()
        except Exception as e:
            LOG.exception("Stop connection exception.")

    def reg_eventFinished(self):
        self.wait_for_reg_event.set()

    def res_eventFinished(self):
        self.wait_for_res_event.set()

    def waitForRegEvent(self, timeout=5, msg="Event timed out."):
        if not self.wait_for_reg_event.wait(timeout):
            self.assertEqual(True, False, msg=msg)

    def waitForResEvent(self, timeout=5, msg="Event timed out."):
        if not self.wait_for_res_event.wait(timeout):
            self.assertEqual(True, False, msg=msg)

    def test_configuration_fsm(self):


        def on_register_receive(ch, method, properties, message):
            LOG.info(properties.app_id)

            if properties.app_id != 'fake-smr':
                msg = yaml.load(message)
                # CHECK: The message should be a dictionary.
                self.assertTrue(isinstance(msg, dict), msg='message is not a dictionary')
                # CHECK: The dictionary should have a key 'specific_manager_name'.
                self.assertIn('specific_manager_name', msg.keys(), msg='no specific_manager_name provided in message.')
                if isinstance(msg['specific_manager_name'], str):
                    # CHECK: The value of 'specific_manager_name' should not be an empty string.
                    self.assertTrue(len(msg['specific_manager_name']) > 0, msg='empty specific_manager_name provided.')
                else:
                    # CHECK: The value of 'specific_manager_name' should be a string
                    self.assertEqual(True, False, msg='specific_manager_name is not a string')
                # CHECK: The dictionary should have a key 'version'.
                self.assertIn('version', msg.keys(), msg='No version provided in message.')
                if isinstance(msg['version'], str):
                    # CHECK: The value of 'version' should not be an empty string.
                    self.assertTrue(len(msg['version']) > 0, msg='empty version provided.')
                else:
                    # CHECK: The value of 'version' should be a string
                    self.assertEqual(True, False, msg='version is not a string')
                # CHECK: The dictionary should have a key 'description'
                self.assertIn('description', msg.keys(), msg='No description provided in message.')
                if isinstance(msg['description'], str):
                    # CHECK: The value of 'description' should not be an empty string.
                    self.assertTrue(len(msg['description']) > 0, msg='empty description provided.')
                else:
                    # CHECK: The value of 'description' should be a string
                    self.assertEqual(True, False, msg='description is not a string')

                # CHECK: The dictionary should have a key 'specific_manager_type'
                if isinstance(msg['specific_manager_type'], str):
                    # CHECK: The value of 'specific_manager_type' should not be an empty string.
                    self.assertTrue(len(msg['specific_manager_type']) > 0, msg='empty specific_manager_type provided.')
                else:
                    # CHECK: The value of 'specific_manager_type' should be a string
                    self.assertEqual(True, False, msg='specific_manager_type is not a string')

                # CHECK: The dictionary should have a key 'service_name'
                if isinstance(msg['service_name'], str):
                    # CHECK: The value of 'service_name' should not be an empty string.
                    self.assertTrue(len(msg['service_name']) > 0, msg='empty service_name id provided.')
                else:
                    # CHECK: The value of 'service_name' should be a string
                    self.assertEqual(True, False, msg='service_name is not a string')

                self.reg_eventFinished()


        def on_ip_receive(ch, method, properties, message):
            LOG.debug("on_ip_receive %s", message)
            if properties.app_id == 'sonfsmservice1firewallconfiguration1':

                payload = yaml.load(message)

                self.assertTrue(isinstance(payload, dict), msg='message is not a dictionary')

                if isinstance(payload['IP'], str):
                    self.assertTrue(payload['IP'] == "10.100.32.250", msg='Wrong IP address')
                else:
                    self.assertEqual(True, False, msg='IP address is not a string')
            self.res_eventFinished()

        self.smr_proc.start()
        #time.sleep(4)

        self.manoconn.subscribe(on_register_receive, 'specific.manager.registry.ssm.registration')

        self.con_proc.start()
        #time.sleep(4)
        self.waitForRegEvent(timeout=5, msg="Registration request not received.")

        self.manoconn.subscribe(on_ip_receive, 'son.configuration.#')
        #time.sleep(4)
        self.slm_proc.start()
        #time.sleep(4)
        #self.waitForResEvent(timeout=5, msg="Configuration request not received.")
        while True:
            time.sleep(10)



if __name__ == '__main__':
    unittest.main(warnings='ignore')
