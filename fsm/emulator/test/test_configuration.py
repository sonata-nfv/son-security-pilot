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

import unittest
import yaml
import threading
import logging
import time
import sys
import os
from multiprocessing import Process
from vnfrsender import fakeflm
import fake_smr
from sonmanobase import messaging
import vpn_css.vpn_css
import firewall.firewall
import sonfsmvprxsquidconfiguration1.sonfsmvprxsquidconfiguration1

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.getLogger('amqpstorm').setLevel(logging.INFO)
# logging.getLogger("son-mano-base:messaging").setLevel(logging.INFO)
FORMAT = '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s'
logging.basicConfig(level=logging.DEBUG, format=FORMAT)
LOG = logging.getLogger(__name__ if __name__ != "__main__" else __file__ + ':' + __name__)


_register_count = 0
_status_count = 0


class testConfFSM(unittest.TestCase):

    def setUp(self):
        current_dir = os.getcwd()
        self.slm_proc = Process(target= fakeflm)
        self.smr_proc = Process(target= fake_smr.main)
        os.chdir('../vpn-config')
        self.con_proc = Process(target=vpn_css.vpn_css.main, kwargs={'working_dir': os.path.realpath('../vpn-config')})
        os.chdir('../firewall-config')
        self.fw_proc = Process(target= firewall.firewall.main, kwargs={'working_dir': os.path.realpath('../firewall-config')})
        self.cache_proc = Process(target=sonfsmvprxsquidconfiguration1.sonfsmvprxsquidconfiguration1.main, kwargs={'working_dir': os.path.realpath('../cache-config')})
        os.chdir(current_dir)

        self.slm_proc.daemon = True
        self.smr_proc.daemon = True
        # self.con_proc.daemon = True

        self.manoconn = messaging.ManoBrokerRequestResponseConnection('ConfTest')

        self.wait_for_reg_event = threading.Event()
        self.wait_for_reg_event.clear()

        self.wait_for_res_event = threading.Event()
        self.wait_for_res_event.clear()

    def tearDown(self):

        if self.smr_proc and self.smr_proc.is_alive():
            self.smr_proc.terminate()
        del self.smr_proc

        if self.slm_proc and self.slm_proc.is_alive():
            self.slm_proc.terminate()
        del self.slm_proc

        if self.con_proc and self.con_proc.is_alive():
            self.con_proc.terminate()
        del self.con_proc

        if self.fw_proc and self.fw_proc.is_alive():
            self.fw_proc.terminate()
        del self.fw_proc

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
        self.wait_for_reg_event.clear()

    def waitForResEvent(self, timeout=5, msg="Event timed out."):
        if not self.wait_for_res_event.wait(timeout):
            self.assertEqual(True, False, msg=msg)
        self.wait_for_res_event.clear()

    def test_configuration_fsm(self):

        def on_register_receive(ch, method, properties, message):
            LOG.debug('on_register_receive with id=%s, message=%s', properties.app_id, message)

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

                global _register_count
                _register_count += 1
                if _register_count >= 2:
                    self.reg_eventFinished()

        def on_ip_receive(ch, method, properties, message):
            LOG.info('on_ip_receive app_id=%s, message=%s ...', properties.app_id, message[:30])
            payload = yaml.load(message)
            LOG.debug('Payload for on_ip_receive = %s', payload)
            self.assertTrue(isinstance(payload, dict), msg='message is not a dictionary')

            if properties.app_id == 'fake-flm':
                if 'nsr' in payload['content']:
                    self.res_eventFinished()
            elif properties.app_id in ['sonfsmservice1function1css1', 'sonfsmpsa-servicefirewall-vnffirewall-config1']:
                if 'status' in payload:
                    self.assertTrue(payload['status'] == 'COMPLETED')
                    global _status_count
                    _status_count += 1
                    if _status_count >= 2:
                        self.res_eventFinished()
            else:
                self.assertEqual(True, False, msg=('Unknown sender: ' + properties.app_id))
                self.fail()
                self.res_eventFinished()


        self.smr_proc.start()
        #time.sleep(4)

        self.manoconn.subscribe(on_register_receive, 'specific.manager.registry.ssm.registration')

        self.fw_proc.start()
        self.con_proc.start()
        self.cache_proc.start()
        self.waitForRegEvent(timeout=5, msg="Registration request not received.")

        self.manoconn.subscribe(on_ip_receive, vpn_css.vpn_css.CssFSM.get_listening_topic_name() + '.#')
        #time.sleep(4)
        self.slm_proc.start()
        time.sleep(10)
        self.waitForResEvent(timeout=5, msg="Configuration request not received.")
        time.sleep(3)

        self.waitForResEvent(timeout=25, msg="Status responses not received.")


if __name__ == '__main__':
    unittest.main(warnings='ignore')
    unittest.main()
